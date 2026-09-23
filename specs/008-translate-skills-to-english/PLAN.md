# PLAN 008 — Skills, agents and tests translated into English

## Owner summary

- **Approach:** the seven skills and four agents are translated one to one, file by file;
  the blocks that tests pin as identical (configuration, language, section map, stage
  contract, escalation triggers) are translated first, once, from the English text fixed in
  this plan, and copied into every file. Each step retargets the structural tests that pin
  the file it translates, keeping every assertion. At the end a new test module keeps Polish
  out of skills, agents, tests and graders (an explicit allowlist for the Polish templates,
  the section map and the Polish fixture), and a one-off script compares the code spans of
  each skill and agent with `main` to prove the translation is one to one. The full eval
  suite runs after the PR is open, on your command, and its receipt is committed on the PR
  branch.
- **Main risks:** a translated sentence that changes a rule the eval suite does not cover
  (mitigated by the one-to-one span comparison and the retargeted tests, proven only by the
  eval run after the PR opens); any `plugin/` change after the eval run invalidates the
  receipt's fingerprint, so the run must come after the final review's fixes; one released
  `plugin/CHANGELOG.md` line (0.5.0) and one unreleased 0.6.0 line quote Polish headings
  and are reworded so the allowlist test holds; the README and `templates/sections.md` still say
  stages "name a section by both literals" and are corrected to the English-only naming
  the SPEC decides.
- **New dependency:** no
- **Data migration:** no — no configuration key changes (SPEC → "Owner decisions")
- **Manual scenarios for the owner:** 2 — command the full eval run once the PR is open
  (AC8), and the release canary on the Polish consumer, including a Polish request that
  must trigger the right skill (AC10).

## Approach

### Base and scope

The branch point is `4bbe647` (`git merge-base origin/main HEAD`); every "on `main`"
comparison below uses it. Files translated: `plugin/skills/*/SKILL.md` (7),
`plugin/agents/*.md` (4), three eval cases, the test modules that pin skill prose, the
comments of every test module. Files left Polish by design: `plugin/templates/*.pl.md`,
`plugin/templates/docs/*.pl.md`, `plugin/templates/sections.md` (rows), the
`plan-review-approves-polish-owner-decision` fixture, the `init-without-questions` prompt,
and the data in `test_templates_language.py`, `test_eval_cases.py`,
`test_init_templates.py` that pins them. No eval is run during implementation (SPEC →
Owner decisions: only after the PR opens, on the owner's command).

### Translation rules (bind every step)

1. One to one: same bullets, same order, same numbering, same emphasis (`**…**`,
   UPPERCASE words such as `NIE`→`NOT`, `ZAWSZE`→`ALWAYS`, `W CAŁOŚCI`→`IN FULL`), same
   code spans. No rewording beyond what English needs (Stage 6 does that).
2. A code span without Polish text stays byte-identical. A span with Polish text (letters
   or Polish placeholder words: `<wersja>`, `<NAZWA>`, `<typ>`, `<komunikat>`,
   `<zakres UI>`, `plik:linia`, `<ścieżka …>`) gets the English equivalent (`<version>`,
   `<NAME>`, `<type>`, `<message>`, `<UI scope>`, `file:line`, …). `<nr>` in
   `gh pr checks <nr> …` stays (pinned, and reads as "number" in English).
3. A section named as „Polish" (`## English`) becomes `## English` alone, or "English" in
   quotes where the original quoted a name; the Polish twin is dropped — it comes only
   from the section map (SPEC → Decisions). Quotes „…" become "…".
4. `STOP`, `RESULT: ESCALATE`, `(Recommended)`, severity tokens, metric keys, commit
   message templates and every path stay as they are.
5. Frontmatter `description` and `argument-hint` are translated (the agents' `name`,
   `skills`, `model` stay).

### Headings the tests pin (English literal to use)

| Polish (on `main`) | English | Where |
|---|---|---|
| `## Konfiguracja projektu` | `## Project configuration` | 6 stage skills |
| `## Język` | `## Language` | 6 stage skills |
| `## Mapa sekcji` | `## Section map` | 6 stage skills |
| `## Szablon SPEC.md` / `## Szablon PLAN.md` | `## SPEC.md template` / `## PLAN.md template` | idea / plan |
| `## Kroki` | `## Steps` | idea, plan, plan-review, init |
| `## Tryb report` / `## Tryb apply` | `## Report mode` / `## Apply mode` | final-review |
| `## Bramka: końcowe review` | `## Gate: final review` | ship |
| `## Protokół wyniku` | `## Result protocol` | ship |
| `## Kontrakt agenta etapu` | `## Stage agent contract` | ship + 4 agents |
| `## Wyzwalacze eskalacji (wiążące dla wszystkich agentów)` | `## Escalation triggers (binding on every agent)` | ship + 4 agents |
| `## Zakres zapisu (bezwzględny)` | `## Write scope (absolute)` | init |
| `4. **Wygeneruj pliki**` | `4. **Generate the files**` | init |
| `5. **Finał — …` | `5. **Finish — the plan's Definition of Done:**` | implement |
| `4. **Zapisz raport**` | `4. **Write the report**` | final-review |

Other headings (`## Wejście / wyjście` → `## Input / output`, `## Guardraile` →
`## Guardrails`, `## Stan` → `## State`, `## Zamknięcie` → `## Closing`, `## Przebieg` →
`## Procedure`, `## Zasady nadrzędne` → `## Overriding rules`, `## Pętla samokorekty
(obowiązkowa dla każdego kroku)` → `## Self-correction loop (mandatory for every step)`,
`## WAŻNE — konsekwencja statusu` → `## IMPORTANT — what the status triggers`,
`## Uruchamianie agenta etapu` → `## Starting a stage agent`, `## Handoff`) are free but
must stay one per original heading; cross-references to them ("Result protocol") follow.

### The shared blocks — the English text

Written once and pasted character-identical into every file that carries the block
(tests: `test_the_configuration_block_is_two_bullets_everywhere`,
`test_the_language_block_is_identical_everywhere`, `test_every_stage_reads_the_section_map`,
`test_every_agent_carries_the_contract`). Line wrapping at ≤ 92 columns like today; the
wording below is binding, the wrapping is not.

`## Project configuration`

```markdown
- Read `.claude/workflow.json`; no file = the defaults from the plugin README → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` etc. = values from this configuration (keys in the README).
```

`## Language`

```markdown
- Files you write into the repository (SPEC, PLAN — every section, including decision
  entries, the review log, deviations and the final review report) and the PR description
  are written in the language from `language` in `.claude/workflow.json`; a missing key or
  a value other than `en`/`pl` = `en`. You name a section by its English heading and accept
  either heading from the section map (the "Section map" section).
- Always in English, regardless of `language` and the session: commit messages, PR titles,
  branch names and spec slugs, the `RESULT` block keys, metric keys and severity tokens.
- The conversation with the owner — questions, escalations, summaries and the handoff — in
  the Claude Code session language, never by `language`.
```

`## Section map`

```markdown
- Before you look for a section in a SPEC or PLAN, load the section map
  `${CLAUDE_PLUGIN_ROOT}/templates/sections.md` with the `Read` tool (key → Polish heading →
  English heading). You name a section by its English heading and accept either heading
  the map gives.
- A failed read of the map or a template ends the stage — you do not guess headings and do
  not rebuild a template from memory. Under `/pipeline:ship`: `RESULT: ESCALATE`; run on
  its own: STOP with the same message to the owner. The message gives the file path and
  the rule to add to `permissions.allow` (the project's `.claude/settings.json` or the user
  settings): `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)`, and for a
  `--plugin-dir` clone — `Read(//<plugin directory path without the leading />/**)`; you
  read `<marketplace>` from the expanded path `${CLAUDE_PLUGIN_ROOT}`
  (`…/plugins/cache/<marketplace>/pipeline/<version>`); when the guard has already shown a
  warning with a ready rule, you give that rule.
```

`## Stage agent contract` (ship + 4 agents)

````markdown
Binding on every agent started by `/pipeline:ship`:

- You carry out the loaded stage skill. You cannot ask the owner (`AskUserQuestion` is
  unavailable). Wherever the skill says to ask, to wait or to STOP — you end your work
  with a `RESULT: ESCALATE` block.
- Owner decisions from SPEC.md and PLAN.md → `## Owner decisions` are binding; do not
  escalate again a matter already settled.
- You record state in the spec files and in commits, never only in the reply.
- Language: spec files and the PR description in `language`; commits, the PR title and the
  RESULT block keys in English; the orchestrator shows the ESCALATION and SUMMARY text to
  the owner in the session language.
- You write the stage metrics yourself into the flat `metrics:` block in the SPEC.md
  frontmatter: counters are integers, timestamps `%Y-%m-%dT%H:%M`, `escalations` from the
  start. `escalations` is incremented only by the orchestrator — a stage agent does not
  change it.
- The final reply starts with the block:

```
RESULT: DONE | ESCALATE
STATUS: <spec status after the stage>
METRICS: <key=value; …>
ESCALATION: <only on ESCALATE — problem; options (≤ 4); recommendation; why>
SUMMARY: <≤ 10 lines; for reviewer/report — the findings table: id | severity | one sentence>
```
````

`## Escalation triggers (binding on every agent)`

```markdown
- a new dependency or a major version bump of an existing one,
- a data migration (the `migrations` section of the configuration),
- a gap or contradiction in the SPEC,
- a blocker from the plan review that the reviewer cannot fix in the plan itself,
- a deviation from the plan that changes the scope, the architecture or the data schema,
- the self-correction loop exhausted (the 4th iteration on the same error),
- a test finds a product defect whose fix goes beyond the plan's scope or the owner
  decisions — instead of working around it by changing the test or the test data,
- a conflict on `git merge origin/main`.
```

`## SPEC.md template` (idea; `plan` the same with `PLAN`, and "chosen by the current
`language`, not by the language of the SPEC", and "PLAN has exactly its headings")

```markdown
You load the template with the `Read` tool — one file, chosen by `language`:

- `pl` → `${CLAUDE_PLUGIN_ROOT}/templates/SPEC.pl.md`;
- `en`, a missing key or any other value → `${CLAUDE_PLUGIN_ROOT}/templates/SPEC.en.md`.

You load only that one file. You do not translate the template or merge it with the other
one — the SPEC has exactly its headings and frontmatter. A failed read of the template →
you follow the "Section map" section (stop with the message; you do not rebuild the
template from memory).
```

### Tests retargeted — every assertion kept

Polish token → English token (the assertion around it is unchanged):

- `plugin/tests/test_language_contract.py`: `## Język`→`## Language`; `angielsku`→`English`
  (language block item 2, agent contract); `sesji`→`session` (item 3, ship Gate and Result
  protocol); `## Kontrakt agenta etapu`→`## Stage agent contract`;
  `## Szablon {document}.md`→`## {document}.md template`; `brak klucza`/`inna wartość`→
  `a missing key`/`any other value`; `## Mapa sekcji`→`## Section map`;
  `mapa sekcji w README`→`section map in the README`; `„Mapa sekcji`→`"Section map"`;
  `## Kroki`→`## Steps`; `nie tłumaczysz`→`do not translate` (plan step 5 must say "you do
  not translate or change the SPEC"); `## Tryb apply`→`## Apply mode`; `angielsk`→`English`
  (the `gh pr create` bullet); `## Bramka: końcowe review`/`## Protokół wyniku`→
  `## Gate: final review`/`## Result protocol`; `warto poprawić`→`worth fixing` (the
  untokenised label must not appear). The block test also asserts `"either"` in the map
  block (it accepts either heading).
- `plugin/tests/test_stage_skills.py`: `Konfiguracja projektu`→`Project configuration`;
  `rozważ`/`warto`→`consider`/`worth`; `widok szeroki`/`widok wąski`/`szeroki i wąski`→
  `wide view`/`narrow view`/`wide and narrow`; `5. **Finał`→`5. **Finish`;
  `4. **Zapisz raport`→`4. **Write the report`; `## Tryb apply`→`## Apply mode`;
  `metryk` dropped from the README guard with its Polish comment (`metric` covers English);
  `Metryki workflow`→`Workflow metrics`.
- `plugin/tests/test_stage_contract.py`: `CONTRACT_HEADINGS`→`## Stage agent contract`,
  `## Escalation triggers`; `` `escalations` zwiększa wyłącznie orkiestrator ``→
  `` `escalations` is incremented only by the orchestrator ``; `na pierwszym planie`→
  `in the foreground`; `Na wynik agenta etapu czekasz, zanim pójdziesz dalej.`→
  `You wait for the stage agent's result before you go on.`; `skill `ship` tego pluginu`→
  `` this plugin's `ship` skill ``; the agent check forbids `skill `ship`` and
  `` `ship` skill ``.
- `plugin/tests/test_init_skill.py`: `Zakres zapisu (bezwzględny)`→`Write scope (absolute)`;
  `<plugin>--v<wersja>`→`<plugin>--v<version>`; `kszta`→`shape`;
  `**Bez `enabledPlugins`**`→`` **No `enabledPlugins`** ``; `i w `enabledPlugins``→
  `` and in `enabledPlugins` ``; `tekst`/`prozą`→`text`/`prose`; `istniejącą wartość`/
  `istniejąca wartość`→`existing value`; `Wyjątek — `language``→`` Exception — `language` ``;
  `ustawiasz `en``→`` you set `en` ``; `komenda pełnej weryfikacji`→
  `full verification command`; `templates/docs/<NAZWA>.<language>.md`→
  `templates/docs/<NAME>.<language>.md`; `istniejących dokumentów nie tłumaczysz ani nie
  podmieniasz`→`you do not translate or replace existing documents`; `że istniejące
  dokumenty zostały w dotychczasowym języku`→`that existing documents stayed in their
  previous language`; `ta sama wartość`→`the same value`.
- `plugin/tests/test_no_domain_references.py`: `**Wygeneruj pliki**`→`**Generate the files**`.
- `plugin/tests/test_eval_cases.py`: `init-without-questions` → prefix
  `The response is incorrect when`, tokens `"pl"`, `TODO`, `Polish`.

The translated skill must contain each English token verbatim; when the natural English
differs, the implementer changes skill and test together and lists the pair in
`## Deviations`.

### New checks (AC1–AC4, AC7)

- `plugin/tests/test_english_only.py` (new; plugin/tests must run from a bare `plugin/`
  checkout, and no basename may repeat in `tests/`):
  - `POLISH_LETTERS` written as escapes (`"ąćęłńóśźż"`
    plus upper case), so the module carries no Polish letter; `test_readme.POLISH`,
    `test_eval_cases.POLISH` and `tests/test_documents.POLISH` switch to escapes too (or
    import it).
  - AC1 `test_skills_and_agents_have_no_polish` — every file under `skills/` and `agents/`.
  - AC2 `polish_files(root, skip)` helper + `test_polish_lives_only_in_the_allowlist`:
    every file under `plugin/` (`rglob`, skipping `evals/results/` and `__pycache__`,
    skipping files that are not UTF-8) whose text holds a Polish letter must match
    `ALLOWLIST` = `templates/*.pl.md`, `templates/docs/*.pl.md`, `templates/sections.md`,
    `evals/plan-review-approves-polish-owner-decision/scaffold.sh`,
    `evals/init-without-questions/case.yaml`, `tests/test_templates_language.py`,
    `tests/test_eval_cases.py`, `tests/test_init_templates.py`; and
    `test_the_allowlist_is_live`: each non-glob entry exists and holds Polish, each glob
    matches at least one file (the list cannot rot).
  - AC3 `polish_in_python_names(path)` helper + `test_test_code_is_english`: for every
    `.py` under `plugin/tests/`, `tokenize` COMMENT tokens, `ast` docstrings (module, class,
    function) and every `FunctionDef`/`AsyncFunctionDef`/`ClassDef` name hold no Polish
    letter.
- `tests/test_documents.py` gains `test_repository_tests_are_english` (AC2 for `tests/`:
  no file with a Polish letter, empty allowlist) and AC3 for `tests/*.py`, importing both
  helpers from `test_english_only` (the module already imports from `plugin/tests`).
- `plugin/tests/test_language_contract.py`: `test_sections_are_named_by_both_headings` and
  `test_the_both_headings_check_sees_wrapped_quotes` are replaced (AC4):
  - `test_no_polish_heading_is_named` — for all 7 skills and 4 agents, no map row whose
    literals differ has its Polish heading text (`heading_text(polish)`) in the file
    (regex with `(?<!\w)` / `(?!\w)` boundaries on the whitespace-normalised full text, so
    `Cel` or `Kroki` without a Polish letter are caught);
  - `test_quoted_headings_are_english_map_literals` — every code span outside fences that
    starts with `#` or `**` is an English literal of a map row (explicit
    `OTHER_HEADINGS = set()` for a legitimate non-SPEC/PLAN heading, with a comment);
  - `test_the_heading_checks_see_wrapped_spans` — the helper finds a span broken over two
    lines and `heading_text` strips `#`, `**` and a trailing colon (English examples).
- AC7 in `plugin/tests/test_eval_cases.py`: `test_graders_and_descriptions_are_english`
  (every case's `graders/criteria.md` and its `description:` line); `test_prompts_are_english`
  (the whole `case.yaml` of `guard-blocks-main-push` and `init-keeps-manual-edits` has no
  Polish letter; the first contains `git push origin main`, the second
  `documents in Polish` and `## House rule`); `test_the_polish_prompt_stays` (the
  `init-without-questions` prompt still holds Polish letters) — its grader tokens come from
  the retargeted `INIT_LANGUAGE_CASES`. `test_new_cases_are_english` and
  `test_the_new_init_case_is_english` stay.

### Eval cases

- `guard-blocks-main-push`: grader and `description` in English; prompt in English with
  the same meaning; `scaffold.sh` README text → `# Fundraiser` / "A tool for running
  charity collections." and the remote `fundraiser.git` (the scaffold is not on the
  allowlist, and the content is incidental to the guard).
- `init-keeps-manual-edits`: grader, `description`, prompt in English; the project becomes
  "Fundraiser" (the Polish name carried `ó`), "documents in Polish" stays, the added
  section is `## House rule` in prompt and grader alike.
- `init-without-questions`: `description` and grader in English; the prompt stays Polish;
  the incorrect paragraph names setting `language` to `"pl"` because the conversation is in
  Polish, Polish documents, and a `TODO` at `language`.

### Documents (AC9) and two statements made false by the translation

- `CONTRIBUTING.md` → Language: skills and agents are English; Polish lives in the
  `*.pl.md` templates and `plugin/templates/sections.md` (and the Polish eval fixture);
  keep the word "Polish" (pinned) and drop "Stage 8"/"still in Polish" (the token list in
  `test_contributing_covers_the_workflow` swaps `Stage 8` for `sections.md`).
- `docs/CONVENTIONS.md` → Language: bullets 2–3 say README, docs, CHANGELOG, skills,
  agents, tests and graders are English; Polish only in the `*.pl.md` templates, the
  section map and the Polish fixture, enforced by `plugin/tests/test_english_only.py`.
- `docs/DECISIONS.md`: one row dated 2026-09-23 — translation one to one in 0.6.0 (SPEC
  008), stages name a section by its English heading with the map as the one Polish ↔
  English bridge, Polish allowlisted; "Amends the 2026-09-17 and 2026-09-21 rows" that kept
  skills Polish, and the naming clause of the 2026-09-23 section-map row.
- `plugin/CHANGELOG.md` 0.6.0: a `### Changed` bullet (skills, agents, tests and graders
  English, one to one; sections named by their English heading, Polish only in the map and
  the `*.pl.md` templates) and one consumer-impact sentence ("no configuration change; a
  `"language": "pl"` consumer keeps Polish specs, plans and documents") appended to the
  existing 0.6.0 `**consumer impact:**` paragraph, not a second marker; the 0.6.0 bullet
  "`## Mapa sekcji` block" becomes "`## Section map` block"; version stays `0.6.0`.
- `plugin/README.md` → Section map and `plugin/templates/sections.md` intro: "Stages name a
  section by both literals" becomes "Stages name a section by its English literal and
  accept either when reading" — the SPEC's naming decision, otherwise the source of truth
  contradicts the skills (rows of the map untouched).
- `docs/ROADMAP.md`: the Stage 8 item ticked, with `(specs/008-translate-skills-to-english/SPEC.md)`.

### AC6 — the span comparison (one run, output into this plan)

A scratch script (implementer's scratchpad, not committed), `span_diff.py`:
for each of the 11 files, `old = git show 4bbe647:<path>`, `new = <working tree>`; drop
fenced blocks (lines between ```` ``` ```` markers), collapse whitespace, take
`re.findall(r"`([^`]+)`")` as a multiset; print `removed = old − new` and
`added = new − old`, each removed span classified as `map` (equals a Polish literal of
`templates/sections.md`), `polish` (holds a Polish letter or a word listed in rule 2) or
`OTHER`, and each added span as `english-twin` (an added span that translates a removed
`polish` one — paired by the implementer) or `OTHER`. The per-file counts go into
End-to-end → Automatic; every `OTHER` goes into `## Deviations` with its reason.

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1–6, 10 | `plugin/tests/test_english_only.py::test_skills_and_agents_have_no_polish` |
| AC2 | 8, 9, 10 | `test_english_only.py::test_polish_lives_only_in_the_allowlist`, `::test_the_allowlist_is_live`; `tests/test_documents.py::test_repository_tests_are_english` |
| AC3 | 9, 10 | `test_english_only.py::test_test_code_is_english`; `tests/test_documents.py::test_repository_test_code_is_english` |
| AC4 | 1, 7 | `test_language_contract.py::test_no_polish_heading_is_named`, `::test_quoted_headings_are_english_map_literals`, `::test_every_stage_reads_the_section_map`, `::test_a_failed_read_stops_the_stage` |
| AC5 | 1, 2 | `test_language_contract.py::test_the_language_block_is_identical_everywhere`; `test_stage_skills.py::test_the_configuration_block_is_two_bullets_everywhere`, `::test_the_configuration_block_keeps_the_fallback`; `test_stage_contract.py::test_every_agent_carries_the_contract` |
| AC6 | 12 | the span comparison run, recorded in End-to-end → Automatic and `## Deviations` |
| AC7 | 8 | `test_eval_cases.py::test_graders_and_descriptions_are_english`, `::test_prompts_are_english`, `::test_the_polish_prompt_stays`, `::test_init_language_cases_name_the_wrong_behaviour` |
| AC8 | — (after the PR opens) | End-to-end → Manual 1: `bash scripts/eval.sh` green, receipt committed, fingerprint check |
| AC9 | 9, 11 | `tests/test_documents.py::test_contributing_covers_the_workflow`, `::test_conventions_state_english_skills`, `::test_decisions_record_the_translation`, `::test_roadmap_ticks_the_translation`; `plugin/tests/test_readme.py::test_the_changelog_records_the_translation` |
| AC10 | — (release) | End-to-end → Manual 2: the canary on the Polish consumer |
| AC11 | every step, DoD | `bash scripts/check.sh` |

## Steps

- [x] 1. The shared blocks and the template choice — files: the six stage
      `plugin/skills/*/SKILL.md` (`## Project configuration`, `## Language`,
      `## Section map`; in `idea` and `plan` also `## SPEC.md template` /
      `## PLAN.md template`), `plugin/skills/ship/SKILL.md` and `plugin/agents/*.md`
      (`## Stage agent contract`, `## Escalation triggers (binding on every agent)`), from
      the English text in Approach; `plugin/tests/test_language_contract.py` (language
      block, agent contract, template read, map block, failed read),
      `plugin/tests/test_stage_skills.py` (configuration block),
      `plugin/tests/test_stage_contract.py` (headings, `escalations` sentence),
      `plugin/tests/test_readme.py` (`result_block` still matches: the fence keeps its
      field names).
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py plugin/tests/test_readme.py plugin/tests/test_plugin_structure.py`
- [x] 2. `ship` and the four agents, the rest — files: `plugin/skills/ship/SKILL.md`
      (frontmatter, intro, `## State` table, `## Start`, `## Starting a stage agent`,
      `## Result protocol`, `## Gate: final review` with the option labels
      "Accept `blocker` and `worth-fixing`, reject `nit` (Recommended)" / "Accept all" /
      "I will choose one by one" / "Only `blocker`", `## Closing`, `## Guardrails`),
      `plugin/agents/{planner,plan-reviewer,implementer,reviewer}.md` (frontmatter
      `description`, intro, `METRICS` lines — the visual sentence in `implementer.md` stays
      one sentence naming `verify.scopes` and `<docs.conventions>`);
      `plugin/tests/test_stage_contract.py` (foreground, waiting sentence, `ship` skill
      reads), `plugin/tests/test_language_contract.py` (ship session-language test, and
      the `## Gate: final review` section read in `test_severities_are_tokens`),
      `plugin/tests/test_readme.py` (the comment "while the ship skill is Polish").
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_stage_contract.py plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_readme.py plugin/tests/test_plugin_structure.py && grep -cP '[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]' plugin/skills/ship/SKILL.md plugin/agents/*.md` (the grep prints `0` for each file)
- [x] 3. `idea` and `plan`, the rest — files: `plugin/skills/idea/SKILL.md`,
      `plugin/skills/plan/SKILL.md` (frontmatter, intro, `## Input / output`, `## Steps`
      — plan step 5 keeps "the current `language`", "SPEC" and "do not translate", step 8
      keeps the closing-step tokens —, `## Guardrails`, `## Handoff`);
      `plugin/tests/test_language_contract.py` (`## Steps`, `do not translate`),
      `plugin/tests/test_stage_skills.py` (if a pinned token moved).
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_no_domain_references.py && grep -cP '[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]' plugin/skills/idea/SKILL.md plugin/skills/plan/SKILL.md` (prints `0` twice)
- [x] 4. `plan-review` and `implement` — files: `plugin/skills/plan-review/SKILL.md`,
      `plugin/skills/implement/SKILL.md` (whole files, the fenced self-correction loop
      included; the visual sentence stays one imperative sentence without "consider" /
      "worth"); `plugin/tests/test_stage_skills.py` (visual sentence words, views,
      `5. **Finish`), `plugin/tests/test_language_contract.py` (plan-review step 3).
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_stage_skills.py plugin/tests/test_language_contract.py && grep -cP '[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]' plugin/skills/plan-review/SKILL.md plugin/skills/implement/SKILL.md` (prints `0` twice)
- [ ] 5. `final-review` — files: `plugin/skills/final-review/SKILL.md` (the finding format
      span becomes `` `[blocker|worth-fixing|nit] file:line — scenario (input → wrong behaviour) — fix` ``;
      `4. **Write the report**`; `## Apply mode` step 3 `gh pr create` bullet keeps
      `--title`, "English" and `` `language` ``; `gh pr checks <nr> --json name,workflow,link`
      unchanged); `plugin/tests/test_stage_skills.py` (`## Apply mode`,
      `4. **Write the report`), `plugin/tests/test_language_contract.py` (`## Apply mode`,
      `English`).
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_stage_skills.py plugin/tests/test_language_contract.py && grep -cP '[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]' plugin/skills/final-review/SKILL.md` (prints `0`)
- [ ] 6. `init` — files: `plugin/skills/init/SKILL.md` (whole file; step 2's question
      list keeps `(Recommended)` in question 1 with `language`, `en`, `pl`,
      `.claude/workflow.json` and "existing value"; step 3 keeps
      `"command": "TODO: <verify command>"` and the language names the argument may use —
      "English/angielski, polski/po polsku" become "`en`, `pl` or its name (English,
      Polish)": the Polish words carry Polish letters and a Polish request in an argument is
      understood without them — a wording change beyond one to one, listed in
      `## Deviations`); `plugin/tests/test_init_skill.py`,
      `plugin/tests/test_no_domain_references.py` (`**Generate the files**`, the comment
      on the acronym).
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_init_skill.py plugin/tests/test_no_domain_references.py plugin/tests/test_init_templates.py plugin/tests/test_plugin_structure.py && grep -cP '[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]' plugin/skills/init/SKILL.md` (prints `0`)
- [ ] 7. AC4 heading checks — files: `plugin/tests/test_language_contract.py` (replace
      `test_sections_are_named_by_both_headings` and
      `test_the_both_headings_check_sees_wrapped_quotes` with the three tests in Approach →
      New checks; `test_severities_are_tokens` forbids `worth fixing`; the `quoted()`
      helper keeps backtick spans only). If a check fails on a skill, fix the skill.
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_language_contract.py`
- [ ] 8. Eval cases — files: `plugin/evals/guard-blocks-main-push/{case.yaml,graders/criteria.md,scaffold.sh}`,
      `plugin/evals/init-keeps-manual-edits/{case.yaml,graders/criteria.md}`,
      `plugin/evals/init-without-questions/{case.yaml,graders/criteria.md}` (description
      and grader only), `plugin/tests/test_eval_cases.py` (`INIT_LANGUAGE_CASES`, the AC7
      tests, comments). Graders keep their numbered points and the "incorrect" paragraph
      and the `.claude/` environment paragraph one to one.
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_eval_cases.py plugin/tests/test_plugin_structure.py`
- [ ] 9. Test prose and the changelog's Polish — files: comments and docstrings of every
      `plugin/tests/*.py` and `tests/*.py` that hold Polish letters or say the skills are
      Polish (`test_readme.py` lines around `POLISH` and the "Quoted literals" comment,
      `test_stage_skills.py`, `test_no_domain_references.py`, `test_eval_cases.py`);
      `POLISH` sets as escapes in `plugin/tests/test_readme.py`,
      `plugin/tests/test_eval_cases.py`, `tests/test_documents.py`;
      `plugin/CHANGELOG.md` — 0.6.0 "`## Decyzje właściciela` accepts" → "whose Polish
      owner-decisions heading accepts", 0.6.0 "`## Mapa sekcji` block" → "`## Section map`
      block", 0.5.0 "identical `## Język` block" → "identical language block".
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests tests && grep -lP '[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]' plugin/tests/*.py tests/*.py plugin/CHANGELOG.md` (lists only `test_templates_language.py`, `test_eval_cases.py`, `test_init_templates.py`)
- [ ] 10. AC1–AC3 checks — files: `plugin/tests/test_english_only.py` (new),
      `tests/test_documents.py` (`test_repository_tests_are_english`,
      `test_repository_test_code_is_english`); run once with a planted Polish letter in a
      scratch copy (`tmp_path`) through the helpers to prove they fail — a unit test
      `test_the_checks_catch_a_planted_letter` in the new module (a file, a comment, a
      docstring and a function name each carrying `ą`).
      Automatic verification: `uv run pytest -q -p no:cacheprovider plugin/tests/test_english_only.py tests/test_documents.py && (cd plugin && python3 -m pytest -q -p no:cacheprovider tests/test_english_only.py)`
- [ ] 11. Documents — files: `CONTRIBUTING.md`, `docs/CONVENTIONS.md`, `docs/DECISIONS.md`,
      `docs/ROADMAP.md`, `plugin/CHANGELOG.md` (0.6.0 `### Changed` bullet, consumer-impact
      sentence), `plugin/README.md` (Section map sentence), `plugin/templates/sections.md`
      (intro sentence only), `tests/test_documents.py` (`test_contributing_covers_the_workflow`
      token swap; new `test_conventions_state_english_skills` — the Language section holds
      `*.pl.md` and `sections.md` and not `until translated`;
      `test_decisions_record_the_translation` — a row holding `SPEC 008`, `2026-09-17` and
      `2026-09-21`; `test_roadmap_ticks_the_translation` — the item holding
      `translated into English` starts `- [x]` and links
      `specs/008-translate-skills-to-english/SPEC.md`), `plugin/tests/test_readme.py`
      (`test_the_changelog_records_the_translation` — 0.6.0 `### Changed` names `English`
      and `one to one`, the impact holds `"language": "pl"`, the manifest version is
      `0.6.0`).
      Automatic verification: `uv run pytest -q -p no:cacheprovider tests/test_documents.py plugin/tests/test_readme.py plugin/tests/test_templates_language.py`
- [ ] 12. AC6 span comparison — scratch `span_diff.py` (Approach → AC6) run over the 11
      files against `4bbe647`; counts into End-to-end → Automatic, every `OTHER` into
      `## Deviations`; a span found changed without reason is fixed in the skill (then
      re-run steps 1–7 verification) rather than justified.
      Automatic verification: `python3 <scratchpad>/span_diff.py 4bbe647 && bash scripts/check.sh`

## Risks and traps

- The shared blocks are compared character for character: paste them, do not retype;
  a trailing space or a different dash breaks `test_the_language_block_is_identical_everywhere`
  / `test_every_agent_carries_the_contract`.
- `section()` helpers split on `\n## ` and match `\n{heading}\n` exactly: a skill's own
  heading must be the English literal from the table in Approach, on its own line.
- Word-boundary regexes in AC4: `Cel`, `Kroki`, `Zakres` have no Polish letter, so AC1
  misses them; the boundary check must not flag English words (`Cancel`, `Celsius`) —
  hence `(?<!\w)`/`(?!\w)` and the case-sensitive match.
- Two test modules with one basename in `plugin/tests` and `tests` break collection
  (no `__init__.py`, default import mode): the new module is `test_english_only.py`, and
  `tests/` gets no module of that name.
- `plugin/tests` must pass from a bare `plugin/` checkout: the new module reads only
  `plugin/`; the `tests/` checks live in `tests/test_documents.py`.
- The eval receipt fingerprints `plugin/` (receipt excluded): every change to `plugin/`
  — final-review fixes included — lands before the eval run; a fix after a red run means
  a re-run (SPEC → Owner decisions: two runs, up to $10; pass `--max-cost-usd 5` per run).
- Editing released `plugin/CHANGELOG.md` text (0.5.0, one line): wording only, no fact
  changes; the GitHub Release notes of 0.5.0 keep the old wording.
- `init` step 3 lists "angielski, polski/po polsku" as argument names; dropping the Polish
  words is required by AC1; the eval case `init-writes-the-chosen-language` passes
  `language: pl` explicitly, and `init-keeps-manual-edits` says "documents in Polish".
- `claude plugin validate --strict plugin/` parses the frontmatter: `description` and
  `argument-hint` stay single-line plain scalars; do not introduce a `: ` or ` #` the
  Polish original did not have (a plain YAML scalar does not allow them) — only init's
  `argument-hint` carries a `: ` today, and it passes validate as it is.
- Line-based checks break on re-wrapping: the `…/templates/{SPEC,PLAN}.en.md` bullet of
  the template block must stay one physical line (`test_idea_and_plan_read_their_template`
  filters lines), and no stage-skill line may carry both `README` and `metric`
  (`test_no_stage_skill_sends_metrics_rules_to_the_readme`).
- The eval suite judges behaviour in English prompts except `init-without-questions`;
  a Polish request triggering the right skill (AC10) is only seen in the canary.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

1. `bash scripts/check.sh` → `ALL GREEN` (validate when `claude` is on PATH, ruff, black,
   pytest over `plugin/tests` and `tests`).
2. `cd plugin && python3 -m pytest -q -p no:cacheprovider tests` → green (bare-plugin run).
3. `grep -rlP '[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]' plugin tests --exclude-dir=results --exclude-dir=__pycache__ | sort`
   → exactly the allowlist: the 8 `*.pl.md` templates (`templates/{SPEC,PLAN,CLAUDE}.pl.md`,
   `templates/docs/*.pl.md`), `templates/sections.md`, the mirror fixture's `scaffold.sh`,
   `init-without-questions/case.yaml`, `test_templates_language.py`, `test_eval_cases.py`,
   `test_init_templates.py`.
4. `claude plugin validate --strict plugin/ && claude plugin validate --strict .` → pass
   (skip with a note when `claude` is not on PATH).
5. The AC6 span comparison (step 12): per-file counts of removed `map` / `polish` spans and
   added `english-twin` spans, and the number of `OTHER` differences (each in
   `## Deviations`) — recorded here.

_(results recorded here by /pipeline:implement)_

### Manual (performed by the owner)

1. **AC8 — after the PR is open, on your command:** the agent runs
   `bash scripts/eval.sh --max-cost-usd 5` on the PR branch head (clean tree; bubblewrap
   and socat installed). Expected: every case passed, `plan-review-approves-polish-owner-decision`
   and `init-without-questions` included, `plugin/evals/last-run.json` with `green: true`,
   `cases_total` = number of case directories, `model: "default"`. Then
   `git ls-tree -r HEAD -- plugin/ | grep -v 'evals/last-run.json' | sha256sum` equals the
   receipt's `plugin_fingerprint`; the agent commits the receipt
   (`test: record the 0.6.0 eval receipt`) and pushes. A red case: fix on the branch,
   re-run once within the $10 spend; still red → escalation.
2. **AC10 — the release canary on the Polish consumer** (`CLAUDE.md` → Commands): in a
   session started with `--plugin-dir <clone>/plugin`, ask in Polish for a new feature
   ("mam pomysł na nową funkcję …") and for a plan of an existing spec ("zaplanuj spec
   NNN"); expected: `/pipeline:idea` and `/pipeline:plan` trigger, the stages read the map,
   and the written SPEC/PLAN is Polish.

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

### 2026-09-23 — /pipeline:plan-review

Findings (counted before fixes): 0 `blocker`, 0 `major`, 5 `minor`.

- R1 `minor` — step 2 translates ship's `## Gate: final review`, but its file list named
  only the session-language test; `test_severities_are_tokens` also reads that section and
  would turn step 2's verification red. Added to step 2.
- R2 `minor` — the frontmatter risk said a `description` with `: ` is safe on one line; a
  plain YAML scalar does not allow `: `. Reworded: keep single-line plain scalars and do
  not introduce `: ` / ` #`.
- R3 `minor` — the shared-block note says wrapping is free, but two checks are line-based
  (the `.en.md` template line; `README` + `metric` on one line). Added to Risks and traps.
- R4 `minor` — 0.6.0 already has a `**consumer impact:**` paragraph
  (`test_the_changelog_names_the_consumer_impact`); the new sentence extends it rather than
  adding a second marker. Clarified in Documents.
- R5 `minor` — dropping "angielski, polski/po polsku" from init step 3 is a wording change
  beyond one to one; step 6 now lists it in `## Deviations`.

Checked and found correct (later stages need not redo it):

- Coverage: every AC1–AC11 has steps and a named test or manual scenario; the matrix
  matches the steps. AC8 and AC10 are correctly outside implementation (SPEC → Owner
  decisions, Decisions).
- Every Polish-pinned assertion in `plugin/tests` and `tests/` was checked against the
  code (`test_language_contract.py`, `test_stage_skills.py`, `test_stage_contract.py`,
  `test_init_skill.py`, `test_no_domain_references.py`, `test_eval_cases.py`,
  `test_readme.py`, `tests/test_documents.py`); the Approach list is complete apart from
  R1. The `test_eval_cases.py` checks of the mirror fixture (its Polish PLAN and SPEC
  headings) stay as allowlisted data.
- The current Polish-letter file set (`grep -rlP` over `plugin` and `tests`) matches the
  plan: after translation exactly the 8 `*.pl.md` templates, `sections.md`, the mirror
  `scaffold.sh`, `init-without-questions/case.yaml` and the three allowlisted test modules
  remain; `plugin/CHANGELOG.md` has exactly the two Polish lines step 9 rewords;
  `tests/fixtures/` holds no Polish.
- The English shared blocks carry every token the retargeted tests assert (`either`,
  `English`, `session`, `a missing key`/`any other value`, `"Section map"`, the failed-read
  tokens, `` `escalations` is incremented only by the orchestrator ``, no `README` in the
  contract) and translate the Polish blocks one to one, except the SPEC-decided naming.
- The heading-like spans in skills and agents today are all map literals, so
  `test_quoted_headings_are_english_map_literals` can start with an empty
  `OTHER_HEADINGS`.
- Rewording the "both literals" sentence in `plugin/README.md` and
  `templates/sections.md`, and amending the 2026-09-23 DECISIONS row, follows SPEC →
  Scope bullet 2 and Decisions; no test pins the old sentence.
- Branch point `4bbe647` = `git merge-base origin/main HEAD`; the fingerprint command in
  Manual 1 is the one `scripts/eval.sh` uses; `--max-cost-usd` is a real flag, and $5 per
  run fits the last measured full run ($3.32 for 8 cases) within the $10 spend.
- No new dependency, no migration, no configuration key change; hooks and `plugin/bin/`
  match no skill prose. The step order has no forward dependency. The PLAN is in English
  (`language: en`).

The plan is ready: no blocker or major remains, every AC is provable by an exact command or
by an owner scenario the SPEC assigns, and no escalation trigger applies.

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
