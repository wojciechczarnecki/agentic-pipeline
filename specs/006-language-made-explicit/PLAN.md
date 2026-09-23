# PLAN 006 — Language made explicit

## Owner summary

- **Approach:** `language` becomes a validated `en`/`pl` key defaulting to `en`, and
  `plugin/README.md` gains a *Language contract* (three groups) and a *Section map*
  (key → Polish → English literal, plus the severity tokens). The inline SPEC and PLAN
  templates move verbatim to `plugin/templates/SPEC.pl.md` / `PLAN.pl.md`, English twins
  are added, and a parity test ties each pair to the map; a snapshot test pins the Polish
  headings to what the inline templates had. Every stage skill gets one identical
  `## Język` block (files in `language`, commits/PR titles/branches English, conversation
  in the session language), the stage contract gets one language bullet in all five
  copies, sections are named by both headings, and severities become the tokens
  `blocker`/`worth-fixing`/`nit` and `blocker`/`major`/`minor`. `/pipeline:init` asks for
  the language first, copies `CLAUDE.<language>.md` and `docs/<NAME>.<language>.md`, and
  falls back to `en` unattended. One new eval case (`init` with `pl`), a stricter
  `init-without-questions`, then docs and the 0.5.0 release.
- **Main risks:** a Polish consumer silently changing (guarded by the verbatim move, the
  snapshot test and the canary); a stage subagent stalling on a permission prompt when it
  `cat`s a template from the plugin cache — measured in step 5 before any skill depends on
  it, escalation if it prompts (it did: owner decision C keeps the templates inline, see
  D1); eval spend — two cases measured 5 times each plus one smoke run of
  each of the three existing cases the change touches, under a $10 ceiling (the
  `docs/CONVENTIONS.md` policy for a new case), then the owner-approved
  receipt after gate 2; `plugin/README.md` may now carry Polish, but only inside code spans
  of the section map, and the test that forbade it is narrowed to exactly that.
- **New dependency:** no.
- **Data migration:** no. (The `language` default flip is configuration, accepted in the
  SPEC's owner decisions; no consumer file is rewritten.)
- **Manual scenarios for the owner:** 1 — the 0.5.0 canary on the Polish consumer, listed
  in the PR description (AC18).

## Approach

### Existing patterns reused

- Section-wise config fallback: `workflow_config.validate` raises `ConfigError`,
  `load_sections` drops the faulty top-level key and reports the message, the guard's
  `read_config` (`plugin/bin/guard.py`) prints it as a warning — a value check for
  `language` inside `validate` gives AC15's "warn and fall back" for free, exactly like
  `protectedBranches` in SPEC 005.
- README ↔ code sync tests (`plugin/tests/test_readme.py`): the configuration table is
  checked against `workflow_config.defaults()`; `strip_code` and `POLISH` are reused by the
  new template tests (`from test_readme import POLISH, strip_code` — `plugin/tests` has no
  `__init__.py`, pytest's `prepend` import mode puts it on `sys.path`, as
  `test_guard_*.py` already do with `from test_guard import …`).
- Identical-block tests: `test_the_configuration_block_is_two_bullets_everywhere`
  (`plugin/tests/test_stage_skills.py`) pins one block across the six stage skills;
  `test_every_agent_carries_the_contract` (`plugin/tests/test_stage_contract.py`) pins the
  contract character-identical across `skills/ship/SKILL.md` and the four agents. The new
  `## Język` block and the new contract bullet ride on these patterns.
- Template reading through the shell: `/pipeline:init` step 4 (`cp`/`cat` from
  `${CLAUDE_PLUGIN_ROOT}/templates/`, never Read/Glob, never from memory). `idea` and
  `plan` adopt the same sentence.
- Eval case layout and the fixture-proof tests: `plugin/evals/init-without-questions/`
  (no scaffold, Polish prompt) and `plugin/tests/test_eval_cases.py`
  (`incorrect_paragraph`, `WRONG_BEHAVIOUR`).
- Eval measurement and ledger: `specs/004-eval-gate-and-canary/PLAN.md` (`--max-cost-usd`
  on every call, a ledger row per call, drafting on `--model sonnet` allowed, measurements
  on the default model only).

### Configuration (AC15)

- `workflow_config.py`: `LANGUAGES = ("en", "pl")`; `defaults()["language"] = "en"`; in
  `validate`, after the type check, `dotted == "language" and value not in LANGUAGES` →
  `ConfigError("`language` has to be one of: en, pl")`. `load()` (and `--check`) raise it
  (exit 1); `load_sections()` drops the key → default `"en"` with that message as the
  problem; the guard prints it and never blocks.
- `plugin/templates/workflow.example.json` keeps `"language": "pl"` (a valid, non-default
  value is the more useful example; init overwrites it with the answer either way).
- README configuration row: `` | `language` | `"en"` | the language of every file the
  pipeline writes into the repository and of PR descriptions — supported `en`, `pl`; any
  other value warns and falls back to `en` (see the language contract below) | ``.

### Language contract and section map in `plugin/README.md` (AC1, AC7, AC9)

Two new subsections under `## Pipeline mechanics`, after `### Escalation triggers`:

- `### Language contract` — three bullet groups, English prose:
  - **Follows `language`:** every file the pipeline writes into the repository — SPEC,
    PLAN (every section, including the review log, deviations, the final review and
    owner-decision entries), the documents `/pipeline:init` generates — and PR
    descriptions. A missing key or a value other than `en`/`pl` means `en`.
  - **Always English, regardless of `language` and the session:** commit messages, PR
    titles, branch names and spec slugs, the `RESULT` block keys, metric keys and severity
    tokens.
  - **Follows the Claude Code session language, never `language`:** questions to the
    owner, escalations shown to the owner, stage summaries and handoffs in the terminal.
  - One sentence: PLAN follows the current `language` even when its SPEC was written in
    another one; nothing already written is translated.
- `### Section map` — one sentence (stages name a section by both literals and accept
  either when reading, so specs written before a language change or before 0.5.0 still
  read correctly), then a table `| key | document | Polish | English |`, every literal in
  a code span, exactly as it appears in the templates:

  | key | document | Polish | English |
  |---|---|---|---|
  | `goal` | SPEC | `## Cel` | `## Goal` |
  | `context` | SPEC | `## Kontekst` | `## Context` |
  | `read-context` | SPEC | `## Przeczytany kontekst` | `## Read context` |
  | `scope` | SPEC | `## Zakres` | `## Scope` |
  | `out-of-scope` | SPEC | `## Poza zakresem` | `## Out of scope` |
  | `requirements` | SPEC | `## Wymagania i kryteria akceptacji` | `## Requirements and acceptance criteria` |
  | `decisions` | SPEC | `## Decyzje i odrzucone alternatywy` | `## Decisions and rejected alternatives` |
  | `owner-decisions` | SPEC | `## Decyzje właściciela` | `## Owner decisions` |
  | `open-questions` | SPEC | `## Pytania otwarte (nieblokujące)` | `## Open questions (non-blocking)` |
  | `assumption` | SPEC | `(założenie)` | `(assumption)` |
  | `owner-summary` | PLAN | `## Streszczenie dla właściciela` | `## Owner summary` |
  | `summary-approach` | PLAN | `**Podejście:**` | `**Approach:**` |
  | `summary-risks` | PLAN | `**Główne ryzyka:**` | `**Main risks:**` |
  | `summary-dependency` | PLAN | `**Nowa zależność:**` | `**New dependency:**` |
  | `summary-migration` | PLAN | `**Migracja danych:**` | `**Data migration:**` |
  | `summary-manual` | PLAN | `**Scenariusze ręczne dla właściciela:**` | `**Manual scenarios for the owner:**` |
  | `approach` | PLAN | `## Podejście` | `## Approach` |
  | `ac-matrix` | PLAN | `## Macierz AC → kroki` | `## AC → steps matrix` |
  | `steps` | PLAN | `## Kroki` | `## Steps` |
  | `step-verification` | PLAN | `Weryfikacja automatyczna:` | `Automatic verification:` |
  | `risks` | PLAN | `## Ryzyka i pułapki` | `## Risks and traps` |
  | `e2e` | PLAN | `## Weryfikacja end-to-end` | `## End-to-end verification` |
  | `e2e-automatic` | PLAN | `### Automatyczna (wykonuje /pipeline:implement)` | `### Automatic (performed by /pipeline:implement)` |
  | `e2e-manual` | PLAN | `### Ręczna (wykonuje właściciel)` | `### Manual (performed by the owner)` |
  | `definition-of-done` | PLAN | `## Definition of Done` | `## Definition of Done` |
  | `owner-decisions` | PLAN | `## Decyzje właściciela` | `## Owner decisions` |
  | `review-log` | PLAN | `## Review log` | `## Review log` |
  | `deviations` | PLAN | `## Deviations` | `## Deviations` |
  | `final-review` | PLAN | `## Final review` | `## Final review` |

  The `##`/`###` rows are the sections (AC7's "one row per section"); the label, marker
  and step-label rows are literals the stages also look for (the owner-summary flags that
  `plan-review` checks, the step verification the implementer's loop runs, the
  `(assumption)` marker `idea` writes), and they keep the English template free of Polish
  (AC8). The H1 lines (`# SPEC NNN — …`, `# PLAN NNN — …`) are not map rows; both
  languages share their prefix.
- Below the map, a severity table `| token | stage | older label read as this token |`:
  `blocker` (plan-review, final-review), `major`, `minor` (plan-review), `worth-fixing`
  (final-review; `warto poprawić`), `nit` (final-review); one sentence: tokens are written
  as code in every language, like metric keys.
- `test_readme_has_no_polish_even_in_code` is replaced by
  `test_readme_polish_only_in_the_section_map`: outside `### Section map` the README has no
  Polish letter at all (code included, as today); inside it, Polish letters occur only
  inside code spans. `test_no_polish_outside_code[README.md]` stays as it is. This follows
  `docs/DECISIONS.md` 2026-09-21 (the README quotes the Polish literals verbatim in code).

### SPEC and PLAN templates (AC5, AC6, AC8, AC17)

- `plugin/templates/SPEC.pl.md` = the body of the ```` ```markdown ```` block in
  `plugin/skills/idea/SKILL.md` (lines 90–139 today), byte for byte, ending with one
  newline; `plugin/templates/PLAN.pl.md` = the body of the ```` ````markdown ```` block in
  `plugin/skills/plan/SKILL.md` (lines 74–138). A one-off check at the step proves it
  (see step 3's verification).
- `SPEC.en.md` / `PLAN.en.md`: the same structure, English headings from the map, English
  placeholders (`<feature name>`, `<1–3 sentences: …>`, `no | yes — …`, `(assumption)`,
  `_(filled in by /pipeline:plan-review)_` …), `Automatic verification:` in the step line;
  the SPEC frontmatter keys identical (`status: spec-draft`, `stage_history:` with
  `"spec-draft — YYYY-MM-DD"`). The H1 prefixes stay `# SPEC NNN — ` / `# PLAN NNN — `.
- New `plugin/tests/test_templates_language.py`:
  - `section_map()` parses the README table (rows under `### Section map` starting with
    `` | ` ``) into `(key, document, polish, english)` with the backticks stripped.
  - `POLISH_SNAPSHOT` — AC17, the headings and frontmatter of today's inline templates,
    as literal lists (taken now, before the move):
    - SPEC frontmatter lines: `---`, `status: spec-draft`, `stage_history:`,
      `  - "spec-draft — YYYY-MM-DD"`, `---`;
    - SPEC headings: `# SPEC NNN — <nazwa feature'a>`, `## Cel`, `## Kontekst`,
      `## Przeczytany kontekst`, `## Zakres`, `## Poza zakresem`,
      `## Wymagania i kryteria akceptacji`, `## Decyzje i odrzucone alternatywy`,
      `## Decyzje właściciela`, `## Pytania otwarte (nieblokujące)`;
    - PLAN headings: `# PLAN NNN — <nazwa feature'a>`, `## Streszczenie dla właściciela`,
      `## Podejście`, `## Macierz AC → kroki`, `## Kroki`, `## Ryzyka i pułapki`,
      `## Weryfikacja end-to-end`, `### Automatyczna (wykonuje /pipeline:implement)`,
      `### Ręczna (wykonuje właściciel)`, `## Definition of Done`,
      `## Decyzje właściciela`, `## Review log`, `## Deviations`, `## Final review`.
    `test_polish_templates_match_the_snapshot` compares every heading line (in order) and
    the frontmatter lines of `SPEC.pl.md` / `PLAN.pl.md` (PLAN has none) with it.
  - `test_template_pairs_have_the_same_structure` (AC8), per document: the `##`/`###`
    lines of each language, mapped to keys through the map, give identical key lists and
    identical levels; a heading with no map row fails; the H1 of both starts with the same
    `# SPEC NNN — ` / `# PLAN NNN — `; frontmatter keys identical.
  - `test_every_map_row_occurs_in_its_template`: each row's Polish literal is in
    `<DOC>.pl.md`, its English literal in `<DOC>.en.md`.
  - `test_english_templates_have_no_polish` over `SPEC.en.md`, `PLAN.en.md` (and, from
    step 7, the English init templates): no Polish letter after `strip_code`.
  - `test_map_keys_are_unique_per_document`.

### The stage skills (AC2, AC3, AC4, AC5, AC7, AC9)

- One identical block in all six stage skills (`idea`, `plan`, `plan-review`, `implement`,
  `final-review`, `ship`), right after `## Konfiguracja projektu`:

  ```markdown
  ## Język

  - Pliki, które zapisujesz w repozytorium (SPEC, PLAN — każda sekcja, także wpisy decyzji,
    review log, deviations i raport końcowego review), oraz treść PR piszesz w języku
    z `language` w `.claude/workflow.json`; brak klucza albo wartość spoza `en`/`pl` = `en`.
    Sekcję wskazujesz oboma nagłówkami i przyjmujesz którykolwiek (mapa sekcji w README
    pluginu).
  - Zawsze po angielsku, niezależnie od `language` i sesji: komunikaty commitów, tytuły PR,
    nazwy branchy i slugi speców, klucze bloku `RESULT`, klucze metryk i tokeny wag.
  - Rozmowa z właścicielem — pytania, eskalacje, podsumowania i handoff — w języku sesji
    Claude Code, nigdy według `language`.
  ```

  Test (`plugin/tests/test_language_contract.py`,
  `test_the_language_block_is_identical_everywhere`): present in all six, identical, three
  bullets; bullet 1 names `` `language` ``, bullet 2 names "commit", "PR" and "angielsku",
  bullet 3 names "sesji". That is AC2's pytest: every skill that writes a spec file names
  `language`, every skill that commits or opens a PR names English for commit messages and
  PR titles.
- The stage contract (`## Kontrakt agenta etapu`, identical in `skills/ship/SKILL.md` and
  `agents/{planner,plan-reviewer,implementer,reviewer}.md`) gets one bullet, after the
  "Stan zapisujesz…" bullet, in all five files at once:
  `- Język: pliki speca i treść PR w \`language\`; commity, tytuł PR i klucze bloku
  RESULT po angielsku; treść ESCALATION i SUMMARY orkiestrator pokazuje właścicielowi
  w języku sesji.` (no "README" in it — `test_the_contract_states_the_metrics_format`
  forbids the word in the contract block) and the owner-decisions heading in
  the contract becomes `` `## Decyzje właściciela` (`## Owner decisions`) ``. Test:
  `test_every_agent_states_its_language_part` — each agent's contract section names
  `` `language` `` and "angielsku" (the identity test keeps the five copies equal).
- `idea`: step 4 reads the template for `language` —
  `` `cat "${CLAUDE_PLUGIN_ROOT}/templates/SPEC.<language>.md"` `` — through the shell,
  never Read/Glob and never from memory (the init sentence); the `## Szablon SPEC.md`
  section and its fenced block are removed; the `(założenie)` marker becomes
  `(założenie)` / `(assumption)` according to the template's language; "Przeczytany
  kontekst", "Decyzje właściciela" and "Pytania otwarte" are named with their English
  twins.
- `plan`: step 5 reads `` `cat "${CLAUDE_PLUGIN_ROOT}/templates/PLAN.<language>.md"` ``
  the same way and states: PLAN.md is written in the current `language`, also when
  SPEC.md is in another language — the SPEC is not translated (AC3). The `## Szablon
  PLAN.md` section and its fenced block are removed; „Streszczenie dla właściciela",
  „Weryfikacja automatyczna" and „Decyzje właściciela" get their English twins.
- `plan-review`: a checklist bullet `- **język:** PLAN (każda sekcja, także Review log)
  w bieżącym \`language\`; niezgodność poprawiasz w miejscu (tłumaczysz plan, SPEC-a nie
  ruszasz) — waga \`major\`.` (AC3); severities written as code — `` `blocker` ``,
  `` `major` ``, `` `minor` `` (AC9); both headings for `## Review log` (same),
  „Streszczenie dla właściciela", „Weryfikacja automatyczna", `## Decyzje właściciela`.
- `implement`: both headings for „Weryfikacja automatyczna", `## Deviations`,
  `## Decyzje właściciela`; the step commit already says `<typ>: <komunikat>` — add "po
  angielsku".
- `final-review`: finding format `` `[blocker|worth-fixing|nit] plik:linia — …` ``; one
  sentence: a report written before 0.5.0 that says `warto poprawić` is read as
  `worth-fixing` (AC9); the standalone decision question recommends accepting
  `` `blocker` `` and `` `worth-fixing` `` and rejecting `` `nit` ``; apply step 3: the PR
  title is an English conventional-commit line
  (`gh pr create --base main --title "<typ>: <angielski komunikat po squashu>"`), the body
  in `language` (AC4); both headings for `## Decyzje właściciela`.
- `ship`: gate 2 — the table and the `AskUserQuestion` in the session language, options
  `„Przyjmij \`blocker\` i \`worth-fixing\`, odrzuć \`nit\` (Recommended)" / „Przyjmij
  wszystkie" / „Wybiorę pojedynczo" / „Tylko \`blocker\`"` (tokens untranslated);
  „Protokół wyniku" — the question built from `ESCALATION` is put to the owner in the
  session language, whatever language the agent wrote it in (AC4); owner decisions are
  recorded in `language`; „Streszczenie dla właściciela" and „Weryfikacja end-to-end →
  Ręczna" get their English twins.
- `plugin/tests/test_language_contract.py` also holds:
  - `test_idea_and_plan_read_their_template_through_the_shell` (AC5): each skill names
    `templates/SPEC.<language>.md` / `templates/PLAN.<language>.md` and `cat`, and has no
    ```` ```markdown ```` / ```` ````markdown ```` block and no `## Szablon` heading;
  - `test_plan_writes_in_the_current_language` (AC3): plan's step 5 names `` `language` ``
    and "SPEC";
  - `test_plan_review_checks_the_language` (AC3): step 3 has a bullet naming
    `` `language` ``;
  - `test_final_review_titles_the_pr_in_english` (AC4): the apply section's PR bullet names
    `--title`, "angielsk" and `` `language` ``;
  - `test_ship_talks_to_the_owner_in_the_session_language` (AC4): the `## Bramka: końcowe
    review` and `## Protokół wyniku` sections both name "sesji";
  - `test_severities_are_tokens` (AC9): final-review has
    `[blocker|worth-fixing|nit]`; plan-review names `` `blocker` ``, `` `major` ``,
    `` `minor` ``; ship's gate section names `` `worth-fixing` ``; in every skill and agent
    each line containing `warto poprawić` also contains `worth-fixing`;
  - `test_sections_are_named_by_both_headings` (AC7): for every map row whose two literals
    differ, in every stage skill and agent file, if the Polish heading text (the literal
    without leading `#`s) occurs inside a code span or a `„…"` quote, the English heading
    text occurs in the same file. Before matching, both the file and the literals are
    normalised: whitespace runs (line wraps included — `ship` wraps "Streszczenie dla
    właściciela" across lines, `implement` wraps "Decyzje właściciela") collapse to one
    space, and the literal's `#`, `**` and trailing `:` are stripped
    (`Weryfikacja automatyczna:` → `Weryfikacja automatyczna`, `**Podejście:**` →
    `Podejście`); without it the test passes vacuously for exactly the twins step 6
    promises.

### `/pipeline:init` (AC10–AC14)

- Templates: `git mv` `plugin/templates/CLAUDE.md` → `CLAUDE.pl.md` and
  `plugin/templates/docs/{PROJECT,ROADMAP,BACKLOG,DECISIONS,CONVENTIONS}.md` →
  `….pl.md`, unchanged (AC11 "keep today's content") except the `## Język` section of
  `CONVENTIONS.pl.md` (AC14); new `CLAUDE.en.md` and `docs/*.en.md` — English, same
  `##` structure and the same `TODO` places, `bash scripts/verify.sh` as the verify
  placeholder (never this repository's check script — `test_no_domain_references.py`).
- `## Język` / `## Language` of the CONVENTIONS templates (AC14), no `TODO` on these lines:
  - pl: `Komunikaty commitów, tytuły PR i nazwy branchy: po angielsku, niezależnie od
    \`language\`.` · `Kod, identyfikatory i komentarze: TODO` · `Dokumentacja (\`docs/\`,
    \`specs/\`) i treść PR: po polsku (\`language: "pl"\` w \`.claude/workflow.json\`).` ·
    `Język rozmowy z agentem nie jest ustawieniem projektu — wynika z sesji Claude Code.` ·
    the existing "Nie mieszamy języków…" line;
  - en: the same five lines in English with `language: "en"`.
- `plugin/skills/init/SKILL.md`:
  - step 2: question 1 becomes the language — `` `language` ``, options `en`
    „(Recommended)" and `pl`, with the reason (English is the default and what outside
    readers expect); then the name/problem, the stack/verify command, production; still
    one round, at most four (AC10);
  - step 3: unattended, the language comes from the argument when it names one (`en`,
    `pl`, or the language itself — English/angielski, polski/po polsku), otherwise `en`,
    without a `TODO:` marker (AC12);
  - step 4: `CLAUDE.md` from `templates/CLAUDE.<language>.md`, `docs/<NAME>.md` from
    `templates/docs/<NAME>.<language>.md` (copied under the target name without the
    language suffix), `language` in `.claude/workflow.json` = the answer (AC11);
  - step 6: a re-run whose language answer differs from the existing `language` updates
    only `language` in `.claude/workflow.json`, does not touch existing documents, and the
    closing message says they stay in the old language (AC13);
  - one sentence (in step 2): questions in the session language — the `language` answer
    governs files, not the conversation.
- Tests: `plugin/tests/test_init_templates.py` — `BASE_FILES` split into shared files and
  `LANGUAGE_FILES` (`CLAUDE`, `docs/PROJECT` …) × `("en", "pl")`; the backlog test per
  language (`Wyzwalacz` / `Trigger`); `test_documents_leave_the_project_specific_parts_open`
  over both languages; new `test_language_twins_share_their_structure` (same sequence of
  heading levels, same number of `TODO` markers) and
  `test_english_init_templates_have_no_polish`; new
  `test_conventions_state_the_language_rules` (AC14: the language section of each
  CONVENTIONS template has no `TODO` on its commit/PR line, names `language`, and the
  session: "sesji" / "session"). `plugin/tests/test_init_skill.py` — `GENERATED` values
  per language (`CLAUDE.{lang}.md` …, both languages must exist); new
  `test_the_language_is_the_first_question` (step 2's first numbered question names
  `` `language` ``, `en`, `pl`, `(Recommended)`; the numbered questions are ≤ 4),
  `test_unattended_language_comes_from_the_argument` (step 3 names "argument", `en`,
  `pl`), `test_templates_are_picked_by_language` (step 4 names `CLAUDE.<language>.md`
  and `<language>.md` under `docs`), `test_a_language_change_leaves_documents_alone`
  (step 6 names `` `language` ``).

### Evals (AC9, AC16)

- New case `plugin/evals/init-writes-the-chosen-language/` (English files, no scaffold,
  `runs: 1`, the same `execution` block as `init-without-questions`). Prompt: an empty
  `git init` directory; run
  `/pipeline:init Tally — a small tool for counting charity collections; language: pl`;
  nobody answers questions; at the end list created files and `TODO:` values, show the
  first five lines of `CLAUDE.md` and of every file in `docs/`, and the `language` value
  written (or, when `.claude/` cannot be written, printed for pasting) in
  `.claude/workflow.json`. The prompt is English on purpose: the Polish documents can only
  come from the argument. Criteria (English, llm): correct when the run finishes without
  asking, `language` is `"pl"` (written or in the printed content), and the shown lines of
  `CLAUDE.md` and `docs/*` are Polish (for example the roadmap title `# Roadmapa`, the
  backlog column `Priorytet`); "The response is incorrect when" names: English documents,
  `"language": "en"` or a `TODO` for `language`, stopping for a question. The eval
  environment blocks `.claude/` writes; printing the files for pasting is accepted (the
  paragraph from `init-without-questions`).
- `init-without-questions` (Polish files, unchanged language): the prompt adds the same
  "show the first five lines … and the `language` value" request; the criteria add: the
  documents are English and `language` is `"en"` without a `TODO:` marker (point 3 gets
  the exception), and the incorrect paragraph names Polish documents, `"pl"` and a `TODO`
  for `language` — the Polish prompt must not leak into the documents.
- `final-review-finds-planted-defect` criteria point 3: `` `blocker` ``,
  `` `worth-fixing` `` or an equivalent label above a nit (the Polish label sentence is
  dropped); `final-review-ignores-false-positive`: "(`blocker`, `worth-fixing` or `nit`)".
- `plugin/tests/test_eval_cases.py`: `INIT_LANGUAGE_CASES` with their wrong-behaviour
  tokens — new case: `English`, `"en"`, `TODO`; `init-without-questions`: `"pl"`, `TODO`
  (its incorrect paragraph starts `Odpowiedź jest niepoprawna, gdy`, so the helper takes
  the prefix as a parameter); `test_the_new_init_case_is_english`;
  `test_final_review_criteria_use_the_tokens` (both final-review criteria name
  `worth-fixing` and not `warto`).

### Documentation and release (AC19, AC20, AC21)

- `plugin/.claude-plugin/plugin.json` → `0.5.0`; `plugin/CHANGELOG.md` `## 0.5.0` with
  `**consumer impact:**` — a consumer without `language` now gets English, add
  `"language": "pl"` to keep Polish; a value other than `en`/`pl` warns and falls back to
  `en`; `init` asks for the language first and generates `CLAUDE.md` and `docs/*` in it;
  commit messages and PR titles are English everywhere; severity tokens
  `worth-fixing` (older reports with `warto poprawić` still read); `### Added` /
  `### Changed`.
- `docs/DECISIONS.md`: four rows (language contract; section map + parity test;
  severity tokens; default `en` with `en`/`pl` only).
- `docs/CONVENTIONS.md` → `## Language`: the plugin bullet says skills and agents stay
  Polish until 0.6.0, templates exist per language (`*.en.md`, `*.pl.md`) and the Polish
  ones survive 0.6.0; commit messages, PR titles and branch names are English for every
  consumer (plugin rule since 0.5.0).
- `CONTRIBUTING.md` → `## Language`: the "templates are still in Polish" clause becomes
  "skills and agents"; templates come in both languages (otherwise the document lies).
- `docs/ROADMAP.md`: the 0.5.0 item ticked; `docs/BACKLOG.md` P3 row from the SPEC's out of
  scope (an eval case for `plan` writing in `language` over a SPEC in another language;
  trigger: a plan written in the wrong language after 0.5.0).

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 2 | `test_readme.py::test_the_language_contract_names_three_groups`, `::test_the_readme_keeps_its_sections` |
| AC2 | 4, 6 | `test_language_contract.py::test_the_language_block_is_identical_everywhere`, `::test_every_agent_states_its_language_part`; `test_stage_contract.py::test_every_agent_carries_the_contract` |
| AC3 | 5, 6 | `test_language_contract.py::test_plan_writes_in_the_current_language`, `::test_plan_review_checks_the_language` |
| AC4 | 6 | `test_language_contract.py::test_final_review_titles_the_pr_in_english`, `::test_ship_talks_to_the_owner_in_the_session_language` |
| AC5 | 3, 5 | `test_language_contract.py::test_idea_and_plan_read_their_template_through_the_shell`; step 5 permission probe (Results) |
| AC6 | 3 | `test_templates_language.py::test_polish_templates_match_the_snapshot`, `::test_every_map_row_occurs_in_its_template` |
| AC7 | 2, 5, 6 | `test_readme.py::test_the_section_map_is_well_formed`; `test_language_contract.py::test_sections_are_named_by_both_headings` |
| AC8 | 3 | `test_templates_language.py::test_template_pairs_have_the_same_structure`, `::test_every_map_row_occurs_in_its_template`, `::test_english_templates_have_no_polish` |
| AC9 | 2, 6, 9 | `test_language_contract.py::test_severities_are_tokens`; `test_eval_cases.py::test_final_review_criteria_use_the_tokens`; `test_readme.py::test_the_section_map_is_well_formed` (severity table) |
| AC10 | 8 | `test_init_skill.py::test_the_language_is_the_first_question` |
| AC11 | 7, 8 | `test_init_templates.py::test_language_twins_share_their_structure`, `::test_english_init_templates_have_no_polish`; `test_init_skill.py::test_templates_are_picked_by_language`; `git diff -M` check in step 7; eval `init-writes-the-chosen-language` |
| AC12 | 8, 9, 10 | `test_init_skill.py::test_unattended_language_comes_from_the_argument`; evals `init-without-questions` and `init-writes-the-chosen-language` (step 10 ledger) |
| AC13 | 8 | `test_init_skill.py::test_a_language_change_leaves_documents_alone` |
| AC14 | 7 | `test_init_templates.py::test_conventions_state_the_language_rules` |
| AC15 | 1 | `test_workflow_config.py::test_defaults_cover_every_documented_key`, `::test_an_unsupported_language_is_rejected`, `::test_load_sections_falls_back_to_english`; `test_readme.py::test_every_config_key_is_documented_with_its_default` |
| AC16 | 9, 10 | `test_eval_cases.py::test_init_language_cases_name_the_wrong_behaviour`, `::test_the_new_init_case_is_english`; eval ledger (5 of 5 per case) |
| AC17 | 3 | `test_templates_language.py::test_polish_templates_match_the_snapshot` |
| AC18 | after gate 2 | PR description checklist (below) |
| AC19 | 11 | `tests/test_documents.py` (links, stage order, versions ascend); `grep` checks in step 11 |
| AC20 | 11 | `test_readme.py::test_changelog_starts_at_the_manifest_version`, `::test_the_changelog_names_the_consumer_impact`; `grep` checks in step 11 |
| AC21 | 11, after gate 2 | `test_no_domain_references.py`; `bash scripts/check.sh`; `bash scripts/eval.sh` receipt, `tests/test_release_gate.py` |

## Steps

- [x] 1. **`language`: `en`/`pl`, default `en`** — files: `plugin/bin/workflow_config.py`,
      `plugin/tests/test_workflow_config.py`, `plugin/README.md` (configuration row only).
      Implement per Approach → Configuration. Tests: `test_defaults_cover_every_documented_key`
      asserts `"en"`; `test_an_unsupported_language_is_rejected` (parametrized `"de"`,
      `"EN"`, `""`: `--check` exit 1, stderr holds "`language` has to be one of: en, pl");
      `test_supported_languages_pass` (`"en"`, `"pl"`: `--check` exit 0);
      `test_load_sections_falls_back_to_english` (`{"language": "de", "production": {"hosts":
      ["x.test"]}}` → problems `["`language` has to be one of: en, pl"]`,
      `config.get("language") == "en"`, hosts kept); the existing `({"language": 7},
      "`language` has to be str")` case stays. The README row lands here because
      `test_every_config_key_is_documented_with_its_default` goes red with the default.
      Automatic verification: `uv run pytest -q plugin/tests/test_workflow_config.py plugin/tests/test_readme.py plugin/tests/test_init_templates.py plugin/tests/test_guard.py`

- [x] 2. **README: language contract, section map, severity tokens** — files:
      `plugin/README.md`, `plugin/tests/test_readme.py`.
      Write `### Language contract` and `### Section map` per Approach. Tests:
      `HEADINGS` gains both (after `### Escalation triggers`, before `## Workflow metrics`);
      `test_the_language_contract_names_three_groups` — the section names, in order, the
      groups "Follows `language`", "Always English", "Follows the Claude Code session
      language", and the tokens `SPEC`, `PLAN`, `PR descriptions`, `commit messages`,
      `PR titles`, `branch names`, `RESULT`, `metric keys`, `severity tokens`,
      `questions`, `escalations`; `test_the_section_map_is_well_formed` — at least one SPEC
      and one PLAN row, keys unique per document, every Polish/English cell is exactly one
      code span, English cells have no Polish letter, the severity table lists `blocker`,
      `major`, `minor`, `worth-fixing`, `nit` and `warto poprawić` on the `worth-fixing`
      row; `test_readme_polish_only_in_the_section_map` replaces
      `test_readme_has_no_polish_even_in_code` (Approach). The map parser lives in this
      file (`section_map()`), step 3 imports it.
      Automatic verification: `uv run pytest -q plugin/tests/test_readme.py tests/test_documents.py`

- [x] 3. **SPEC and PLAN templates per language** — files: `plugin/templates/SPEC.pl.md`,
      `plugin/templates/SPEC.en.md`, `plugin/templates/PLAN.pl.md`,
      `plugin/templates/PLAN.en.md` (all new), `plugin/tests/test_templates_language.py`
      (new).
      Write the test with `POLISH_SNAPSHOT` first (Approach → SPEC and PLAN templates),
      then create the Polish files by moving the inline blocks verbatim and write the
      English twins. The skills keep their inline templates until step 5.
      Automatic verification:
      `uv run pytest -q plugin/tests/test_templates_language.py plugin/tests/test_readme.py plugin/tests/test_no_domain_references.py`
      and the verbatim proof (both must print nothing):
      `diff <(awk '/^```markdown$/{f=1;next} /^```$/{f=0} f' plugin/skills/idea/SKILL.md) plugin/templates/SPEC.pl.md`
      `diff <(awk '/^````markdown$/{f=1;next} /^````$/{f=0} f' plugin/skills/plan/SKILL.md) plugin/templates/PLAN.pl.md`

- [x] 4. **The `## Język` block and the contract bullet** — files: the six
      `plugin/skills/{idea,plan,plan-review,implement,final-review,ship}/SKILL.md` (the block
      only), `plugin/agents/{planner,plan-reviewer,implementer,reviewer}.md` and
      `plugin/skills/ship/SKILL.md` (the contract bullet and the `(## Owner decisions)`
      twin, identical in all five), `plugin/tests/test_language_contract.py` (new).
      Tests: `test_the_language_block_is_identical_everywhere`,
      `test_every_agent_states_its_language_part`.
      Automatic verification: `uv run pytest -q plugin/tests/test_language_contract.py plugin/tests/test_stage_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_plugin_structure.py plugin/tests/test_no_domain_references.py`

- [x] 5. **`idea` and `plan` read their template; PLAN in the current language** — files:
      `plugin/skills/idea/SKILL.md`, `plugin/skills/plan/SKILL.md`,
      `plugin/tests/test_language_contract.py`.
      First the permission probe (AC5 depends on it — a stage subagent cannot answer a
      prompt): in a throwaway consumer under the scratchpad (`git init`, this repository's
      `plugin/templates/settings.json` copied to `.claude/settings.json` with its `TODO`
      marketplace entry removed, `.claude/workflow.json` = `{"language": "en"}`), run
      `claude --plugin-dir <repo>/plugin -p --model haiku --max-turns 3 'Run exactly this Bash command and print its output verbatim: cat "${CLAUDE_PLUGIN_ROOT}/templates/PLAN.en.md" | head -3'`
      — once as written (the variable is not set in the Bash tool's shell, so expect it to
      fail to resolve) and once with the absolute path the skill would carry after
      substitution (`<repo>/plugin/templates/PLAN.en.md` — outside the consumer's working
      directory, like a cache install), and a third time with the real cache path of the
      plugin installed on this machine
      (`ls -d ~/.claude/plugins/cache/*/pipeline/*/templates/CLAUDE.md | tail -1` — the file
      consumers actually read from; the `--plugin-dir` path alone may be treated
      differently). Record all three outcomes under Results. If either absolute
      `cat` is refused or waits for approval → **escalate** (options: an allow rule in
      `templates/settings.json` plus a consumer-impact line; templates under
      `skills/<name>/`; keeping inline templates) — do not work around it.
      Then edit per Approach → The stage skills (`idea`, `plan`), and add
      `test_idea_and_plan_read_their_template_through_the_shell` and
      `test_plan_writes_in_the_current_language`. `test_stage_skills.py`'s `CLOSING_STEPS`
      prefixes (`"8. "` for plan) must still match — keep the step numbering.
      Automatic verification: `uv run pytest -q plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py plugin/tests/test_no_domain_references.py plugin/tests/test_templates_language.py`

- [x] 6. **`plan-review`, `implement`, `final-review`, `ship`: language, tokens, both
      headings** — files: `plugin/skills/{plan-review,implement,final-review,ship}/SKILL.md`,
      `plugin/tests/test_language_contract.py`.
      Edit per Approach → The stage skills. Tests: `test_plan_review_checks_the_language`,
      `test_final_review_titles_the_pr_in_english`,
      `test_ship_talks_to_the_owner_in_the_session_language`, `test_severities_are_tokens`,
      `test_sections_are_named_by_both_headings` (over all six skills and four agents —
      it also proves step 5's `idea`/`plan` edits). Keep `final-review`'s
      `4. **Zapisz raport` and `## Tryb apply` / `5. ` / `6. ` anchors and
      `gh pr checks <nr> --json name,workflow,link` (existing tests).
      Automatic verification: `uv run pytest -q plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py plugin/tests/test_readme.py plugin/tests/test_no_domain_references.py`

- [x] 7. **`init` templates per language** — files: `plugin/templates/CLAUDE.md` →
      `CLAUDE.pl.md`, `plugin/templates/docs/*.md` → `*.pl.md` (`git mv`), new
      `plugin/templates/CLAUDE.en.md` and `plugin/templates/docs/*.en.md`,
      `plugin/templates/docs/CONVENTIONS.{pl,en}.md` language section (AC14),
      `plugin/tests/test_init_templates.py`, `plugin/tests/test_templates_language.py`
      (English init templates join `test_english_templates_have_no_polish`),
      `plugin/tests/test_init_skill.py` (`GENERATED` values only, so it stays green before
      step 8 — the template names in `init`'s text change in step 8, and the
      "generated path is named in the skill" assertion is unaffected).
      Automatic verification:
      `uv run pytest -q plugin/tests/test_init_templates.py plugin/tests/test_init_skill.py plugin/tests/test_templates_language.py plugin/tests/test_no_domain_references.py`
      and `git diff -M --name-status origin/main -- plugin/templates/` shows `R100` for
      `CLAUDE.pl.md`, `PROJECT.pl.md`, `ROADMAP.pl.md`, `BACKLOG.pl.md`, `DECISIONS.pl.md`
      and a rename with changes only for `CONVENTIONS.pl.md`
      (`git diff -M origin/main -- plugin/templates/docs/CONVENTIONS.md plugin/templates/docs/CONVENTIONS.pl.md`
      — both paths, or git cannot pair the rename and shows a whole new file — touches only
      its `## Język` section).

- [x] 8. **`init` skill: the language first, per-language templates, re-run** — files:
      `plugin/skills/init/SKILL.md`, `plugin/tests/test_init_skill.py`.
      Edit per Approach → `/pipeline:init`. Tests:
      `test_the_language_is_the_first_question`,
      `test_unattended_language_comes_from_the_argument`,
      `test_templates_are_picked_by_language`, `test_a_language_change_leaves_documents_alone`;
      the existing step-2/step-3 tests (`AskUserQuestion` before question 1, the prose
      loophole) and `test_the_exempt_skill_only_documents_generated_files` stay green.
      Automatic verification: `uv run pytest -q plugin/tests/test_init_skill.py plugin/tests/test_init_templates.py plugin/tests/test_no_domain_references.py`

- [x] 9. **Eval cases** — files: `plugin/evals/init-writes-the-chosen-language/case.yaml`,
      `…/graders/criteria.md` (new), `plugin/evals/init-without-questions/case.yaml`,
      `…/graders/criteria.md`, `plugin/evals/final-review-finds-planted-defect/graders/criteria.md`,
      `plugin/evals/final-review-ignores-false-positive/graders/criteria.md`,
      `plugin/tests/test_eval_cases.py`.
      Per Approach → Evals. `test_eval_cases.py`'s `cases()` picks the new directory up
      (it has no `scaffold.sh`, so `test_scaffold_runs` skips it); new tests
      `test_init_language_cases_name_the_wrong_behaviour`,
      `test_the_new_init_case_is_english`, `test_final_review_criteria_use_the_tokens`;
      `WRONG_BEHAVIOUR` for `final-review-finds-planted-defect` keeps `nit`, `rejected`,
      `shipping.py`.
      Automatic verification: `uv run pytest -q plugin/tests/test_eval_cases.py && claude plugin validate --strict plugin/`

- [x] 10. **Eval measurement of the two `init` language cases** — files: this PLAN
      (`### Results` → eval ledger), and the two cases' `case.yaml`/criteria only if the
      policy requires a change.
      Commit steps 1–9 first (the ledger names the commit). Policy
      (`docs/CONVENTIONS.md`, Tests): a new case, and `init-without-questions` whose pass
      condition this spec tightens, are measured with 5 runs on the default model; 5 of 5
      → `runs: 1`, 4 of 5 → `runs: 3`, below that sharper criteria (or a skill fix inside
      this plan's scope when the transcript shows the skill at fault) and a new
      measurement. Every call with
      `--max-cost-usd`; optional drafting on `--model sonnet --runs 1 --max-cost-usd 1`,
      at most two calls. Measurement calls:
      `claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none --case init-writes-the-chosen-language --runs 5 --max-cost-usd 3 --json <scratchpad>/eval/measure-init-language.json`
      `claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none --case init-without-questions --runs 5 --max-cost-usd 3 --json <scratchpad>/eval/measure-init-without-questions.json`
      Then one smoke run each of the three existing cases whose skill or criteria this
      plan changes — `init-keeps-manual-edits` (init rewritten in step 8; its prompt says
      "dokumenty po polsku", which step 3 of init now reads as a language),
      `final-review-finds-planted-defect` and `final-review-ignores-false-positive`
      (severity tokens in the skill and in the criteria, step 6 and 9) — so a regression
      surfaces here, inside this plan's budget, not first in the receipt after gate 2:
      `claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none --case <name> --runs 1 --max-cost-usd 1 --json <scratchpad>/eval/smoke-<name>.json`
      (three calls). A smoke failure makes that case "an existing one that fails in any
      run": it gets the 5-run measurement of the policy, and the fix stays inside this
      plan's scope (skill text or criteria), otherwise escalate.
      Budget for this step, smoke runs included: **$10 in total**.
      A ledger row per call (date, case, model, runs, passed, `--max-cost-usd`, cost from
      the JSON, running total). The budget would be exceeded, or a case stays below 4 of 5
      after one criteria revision → **escalate** with the ledger.
      Automatic verification: both measurement JSONs show 5 runs each with ≥ 4 passed, the
      three smoke JSONs show 1 of 1 passed (or the follow-up 5-run measurement ≥ 4 of 5),
      the ledger total ≤ $10, and `uv run pytest -q plugin/tests/test_eval_cases.py`

- [x] 11. **Documentation and release 0.5.0** — files: `plugin/.claude-plugin/plugin.json`,
      `plugin/CHANGELOG.md`, `docs/DECISIONS.md`, `docs/CONVENTIONS.md`, `CONTRIBUTING.md`,
      `docs/ROADMAP.md` (tick 0.5.0), `docs/BACKLOG.md` (P3 row).
      Per Approach → Documentation and release.
      Automatic verification: `bash scripts/check.sh` → ALL GREEN; and
      `test $(grep -c '^| 20' docs/DECISIONS.md) -eq $(( $(git show origin/main:docs/DECISIONS.md | grep -c '^| 20') + 4 ))`
      (four new rows: the contract, the map, the tokens, the default);
      `grep -n '"version": "0.5.0"' plugin/.claude-plugin/plugin.json`;
      `grep -n 'language": "pl"' plugin/CHANGELOG.md`;
      `grep -n '\- \[x\] 0.5.0' docs/ROADMAP.md`;
      `grep -n '\*\.en\.md' docs/CONVENTIONS.md`

### After gate 2 (final-review apply mode, not the implementer)

- AC21: after the gate-2 fixes, `bash scripts/eval.sh` (the full suite, now eight cases,
  default model — the receipt the owner approved in the SPEC) and commit
  `plugin/evals/last-run.json` as the PR's last change under `plugin/`; any later change
  under `plugin/` means running it again. The `docs: close SPEC 006` commit touches only
  `specs/`, so the fingerprint still matches.
- AC18: the PR description carries this checklist for the owner's 0.5.0 canary on the
  Polish consumer (`claude --plugin-dir <clone>/plugin --debug-file /tmp/canary.log`):
  1. `/pipeline:plan` (or `/pipeline:ship` up to `plan-draft`) on a Polish spec yields a
     Polish PLAN with exactly the Polish headings (`## Streszczenie dla właściciela` …);
  2. questions and summaries come in the session language;
  3. `grep -E 'Found [0-9]+ plugins' /tmp/canary.log` equals a plain session's count in
     the same consumer;
  4. the consumer's `.claude/workflow.json` has `"language": "pl"` before the canary (the
     default is now `en`).

## Risks and traps

- **Polish consumer regression.** The Polish templates are moved byte for byte (step 3's
  `diff` proof) and pinned by the snapshot test; the `init` Polish templates are `git mv`
  renames (`R100`) except the CONVENTIONS language section. Placeholders in the Polish
  templates stay Polish; nothing in them is "improved".
- **Permission prompt on template reads.** A stage subagent under `/pipeline:ship` cannot
  answer a prompt (the 0.3.0 metrics-checker lesson, `docs/DECISIONS.md` 2026-09-21);
  `cat` of a file under the plugin cache is outside the consumer's working directory.
  Step 5 measures it before the skills depend on it; `${CLAUDE_PLUGIN_ROOT}` is
  substituted in skill text but absent from the Bash tool's shell, so the skill must hand
  the model the substituted path (the same form `init` uses).
- **The README's Polish.** `test_readme_has_no_polish_even_in_code` would fail the moment
  the section map lands; it is narrowed, not dropped — Polish stays impossible outside the
  map's code spans.
- **The contract lives in five files.** `test_every_agent_carries_the_contract` fails on
  any one-sided edit; step 4 edits all five in one go.
- **Existing anchors in skill tests.** `test_stage_skills.py` locates closing steps by
  prefixes (`8. `, `6. `, `5. **Finał`, `4. **Zapisz raport`, `## Tryb apply` → `5. `/`6. `)
  and the configuration block by `## Konfiguracja projektu`; `test_init_skill.py` by
  `\n{n}. ` step starts, `**Wygeneruj pliki**`, `**Bez \`enabledPlugins\`**`. Adding
  `## Język` and new bullets must not renumber steps or insert a line starting with a
  digit and `. ` inside a closing step.
- **`test_no_domain_references.py`** scans every plugin file: the English templates use
  `bash scripts/verify.sh`, never this repository's check script, and no consumer name.
- **Eval environment.** `claude plugin eval` blocks writes to `.claude/`, so the `language`
  value is judged from the printed content; the grader judges the last message, hence the
  prompt asks the run to show the documents' first lines. The init cases need
  `timeout_seconds: 900` / `max_turns: 80` like their siblings. A granted shell tool needs
  `bubblewrap` and `socat`.
- **Eval fingerprint.** Any change under `plugin/` after the receipt invalidates it; the
  receipt comes after the gate-2 fixes.
- **Guard in this session.** Sessions here run the released 0.4.0 plugin; renames go
  through `git mv` (not a shell write on a guardrail path — the working-tree `plugin/` is
  not the running guard's directory). Should the guard refuse a shell edit, use
  Edit/Write.
- **Language of new texts.** Skill and agent additions are Polish (skills stay Polish
  until 0.6.0); tests, README, CHANGELOG, eval files of the new case and repository
  documents are English; `init-without-questions` stays Polish.
- **Default flip.** Any consumer without `language` switches to English at 0.5.0; the
  CHANGELOG consumer impact says it first, and the canary checklist has the owner confirm
  the Polish consumer sets `"pl"`.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

After step 11:

1. In a throwaway repository under the scratchpad (`git init`,
   `.claude/workflow.json` = `{"language": "de"}`):
   `python3 <repo>/plugin/bin/workflow_config.py --check` → exit 1, stderr
   "`language` has to be one of: en, pl";
   `printf '%s' '{"tool_input":{"command":"ls"},"cwd":"'"$PWD"'"}' | python3 <repo>/plugin/bin/guard.py; echo "exit=$?"`
   → exit 0 with the same message as a warning on stderr.
2. Same repository with `{"language": "pl"}` and with `{}`: `--check` → exit 0.
3. `cat plugin/templates/PLAN.pl.md | grep '^#'` equals the Polish PLAN snapshot lines, and
   `grep '^#' plugin/templates/PLAN.en.md` lists the English headings of AC6 (manual
   eyeball recorded under Results; the tests assert it).
4. `claude plugin validate --strict plugin/` and `claude plugin validate --strict .` → pass.
5. The eval ledger of step 10: `init-writes-the-chosen-language` and
   `init-without-questions` each 5 runs, ≥ 4 passed; the three smoke runs passed (or
   their follow-up measurement ≥ 4 of 5); total ≤ $10.
6. The step 5 permission probe recorded (both absolute-path `cat`s — `--plugin-dir` and
   cache — ran without a prompt).
7. `bash scripts/check.sh` → ALL GREEN.

Record the outputs under Results below.

### Manual (performed by the owner)

- The 0.5.0 canary on the Polish consumer, after merge and before the tag, with the four
  checks of AC18 listed in the PR description.

### Results

_(filled in by /pipeline:implement: the step 5 permission probe, the step 10 eval ledger
— date, step, case, model, runs, passed, `--max-cost-usd`, cost, running total — and the
end-to-end outputs above)_

**Implementation progress (2026-09-23, /pipeline:implement):** steps 1–11 committed green;
self-correction iterations: 2 (step 2 — `PR titles` wrapped across a README line, the README
bullet rewrapped; step 6 — a Python string literal in the new test closed early on the
`"` of a `„…"` quote, fixed with single quotes).

**End-to-end verification (2026-09-23, after step 11):**

1. Throwaway repository, `.claude/workflow.json` = `{"language": "de"}`:
   `workflow_config.py --check` → exit 1, stderr
   `workflow.json: \`language\` has to be one of: en, pl`; `guard.py` on `ls` → exit 0,
   stderr `pipeline guard: \`language\` has to be one of: en, pl; that section falls back to
   the defaults`. (The JSON files were written with Write — this session's guard refuses a
   shell write to `.claude/workflow.json`.)
2. `{"language": "pl"}` and `{}` → `--check` exit 0 both.
3. `grep '^#' plugin/templates/PLAN.pl.md` equals the Polish PLAN snapshot (diff empty);
   `grep '^#' plugin/templates/PLAN.en.md` lists `# PLAN NNN — <feature name>`,
   `## Owner summary`, `## Approach`, `## AC → steps matrix`, `## Steps`,
   `## Risks and traps`, `## End-to-end verification`,
   `### Automatic (performed by /pipeline:implement)`, `### Manual (performed by the owner)`,
   `## Definition of Done`, `## Owner decisions`, `## Review log`, `## Deviations`,
   `## Final review` — AC6's list.
4. `claude plugin validate --strict plugin/` and `claude plugin validate --strict .` →
   `Validation passed` both.
5. Eval ledger above: both `init` language cases 5 of 5, three smoke runs 1 of 1, $5.68.
6. Step 5 permission probe recorded above: the absolute-path `cat`s were **refused** (not
   "ran without a prompt" as this item expected); resolved by owner decision C —
   templates inline, nothing read at run time (deviation D1).
7. `bash scripts/check.sh` → ALL GREEN (1714 passed).

**Step 5 permission probe (2026-09-23, Claude Code 2.1.280, `--model haiku`, `-p`,
`--output-format json`).** Consumer: `git init` under the scratchpad,
`.claude/settings.json` = `plugin/templates/settings.json` without the marketplace entry,
`.claude/workflow.json` = `{"language": "en"}`, `claude --plugin-dir <repo>/plugin`:

| # | command | outcome |
|---|---|---|
| 1 | `cat "${CLAUDE_PLUGIN_ROOT}/templates/PLAN.en.md" \| head -3` | refused — `permission_denials` holds it (and a follow-up `echo "$CLAUDE_PLUGIN_ROOT"`); the variable is not resolved in the Bash tool, as expected |
| 2 | `cat "<repo>/plugin/templates/PLAN.en.md" \| head -3` (the `--plugin-dir` path) | refused — `permission_denials`, the model reports it needs approval |
| 3 | `cat "~/.claude/plugins/cache/wcz-tools/pipeline/0.4.0/templates/CLAUDE.md" \| head -3` (the installed cache) | refused — `permission_denials`, the model asks for approval |
| 3b | the same as 3, run from this repository (a trusted workspace, its own `.claude/settings.json`) | refused — `permission_denials` |

The probe consumer was an untrusted workspace (Claude Code ignored its `permissions.allow`),
so 3b repeats probe 3 in a trusted one: the result does not change — `cat` of a file
outside the working directory asks for approval, and a headless stage subagent cannot give
it. `plugin/templates/settings.json` has no rule that covers it. Per step 5: **escalated**,
the skills still carry their inline templates (step 5 not started beyond the probe).
Owner decision C (below): templates stay inline, pinned to the files — deviation D1.

**Step 10 eval ledger (2026-09-23, Claude Code 2.1.280, default model, all calls with
`--scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none`,
measured on commit `3ec7522`).** No drafting calls on `--model sonnet` were made.

| # | date | case | model | runs | passed | `--max-cost-usd` | cost (USD) | running total |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-09-23 | `init-writes-the-chosen-language` (measurement) | default | 5 | 5 | 3 | 1.9944 | 1.9944 |
| 2 | 2026-09-23 | `init-without-questions` (measurement) | default | 5 | 5 | 3 | 1.8174 | 3.8118 |
| 3 | 2026-09-23 | `init-keeps-manual-edits` (smoke) | default | 1 | 1 | 1 | 0.4618 | 4.2736 |
| 4 | 2026-09-23 | `final-review-finds-planted-defect` (smoke) | default | 1 | 1 | 1 | 0.5864 | 4.8600 |
| 5 | 2026-09-23 | `final-review-ignores-false-positive` (smoke) | default | 1 | 1 | 1 | 0.8196 | 5.6796 |

Both measured cases 5 of 5 → they keep `runs: 1` (policy); the three smoke runs passed, so
no follow-up measurement; total $5.68 of the $10 budget. Every grader verdict was three
PASS votes. Spot check of the final messages: the `pl` case reports `CLAUDE.md` "from the
Polish template" and prints `.claude/workflow.json` for pasting (the eval blocks
`.claude/` writes); `init-without-questions` answers in Polish and reports `CLAUDE.md`
"z szablonu angielskiego" — the prompt's language did not leak into the documents.

## Definition of Done

- [x] all steps ticked
- [x] `bash scripts/check.sh` fully green
- [x] end-to-end verification (automatic) performed, result recorded here
- [x] `docs/ROADMAP.md` updated; `docs/DECISIONS.md`, `docs/CONVENTIONS.md`,
      `docs/BACKLOG.md`, `CONTRIBUTING.md` updated
- [x] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

- 2026-09-23 · implement (step 5) · Question: a headless stage subagent (`claude -p`) is
  refused permission to `cat` a SPEC/PLAN template outside the working directory (the
  `--plugin-dir` path, the installed cache path and the unresolved `${CLAUDE_PLUGIN_ROOT}`
  path), so `idea`/`plan` cannot read their templates at runtime without stalling
  `/pipeline:ship`. Options: (A) an allow rule in `plugin/templates/settings.json`;
  (B) templates as skill reference files; (C) templates stay inline. · Decision: **C**.
  The SPEC/PLAN templates stay inline in `idea` and `plan`, as a Polish and an English block;
  the `*.pl.md`/`*.en.md` files remain the tested source, and a pytest check pins each inline
  block to its file byte for byte. AC5's "no inline template" reads as "inline, pinned to
  the template files". Nothing is read at runtime; consumers need no settings change.

- 2026-09-23 · final review (gate 2) · Question: which final-review findings to fix?
  · Decision: **accept all** — F1, F2, F3, F4 (worth-fixing) and F5, F6, F7, F8, F9, F10,
  F11, F12, F13 (nits). Rejected: none.

## Review log

### 2026-09-23 — /pipeline:plan-review

Findings (severity counted before the fixes: 0 `blocker`, 1 `major`, 3 `minor`):

- **R1 `major` — step 10 left three affected existing eval cases unexercised.** Steps 6,
  8 and 9 change the init skill (`init-keeps-manual-edits`, whose prompt says "dokumenty
  po polsku" — now read by init as a language) and the final-review severity format and
  criteria (`final-review-finds-planted-defect`, `final-review-ignores-false-positive`).
  Only the two init language cases were measured, so a regression in these three would
  first show in the receipt after gate 2 — rework after the owner's decisions, and a
  5-run policy measurement with no budget. Changed: step 10 adds one smoke run of each
  (`--runs 1 --max-cost-usd 1`), a failing smoke goes through the policy measurement;
  the step budget rises from $8 to $10; owner summary and end-to-end item 5 follow.
- **R2 `minor` — step 7's rename proof could not work.**
  `git diff -M origin/main -- plugin/templates/docs/CONVENTIONS.pl.md` names only the new
  path, so git cannot pair the rename and shows the whole file as added. Changed: the
  command names both the old and the new path.
- **R3 `minor` — `test_sections_are_named_by_both_headings` would pass vacuously for
  the twins it is meant to prove.** Skill quotes wrap across lines (`ship`: "Streszczenie
  dla / właściciela"; `implement`: "Decyzje / właściciela"), and the map's literal rows
  carry markup (`Weryfikacja automatyczna:` with a colon, `**Podejście:**`) that the
  skills' quotes never contain. Changed: the test normalises whitespace and strips `#`,
  `**` and a trailing `:` before matching.
- **R4 `minor` — the step 5 permission probe measured only the `--plugin-dir` path.**
  Consumers read templates from `~/.claude/plugins/cache/<marketplace>/pipeline/<ver>/`,
  which Claude Code may treat differently. Changed: a third probe `cat`s a template under
  the installed cache path (present on this machine, 0.3.4 has `templates/CLAUDE.md`);
  either absolute path prompting → escalate. End-to-end item 6 follows.

Checked and found correct (later stages need not redo it):

- Coverage: every AC1–AC21 has steps and a proving test or a recorded check; the matrix
  matches the step list; AC18 and the receipt part of AC21 are correctly after gate 2.
- Facts against the code: the inline templates sit at `idea/SKILL.md` 89–140 (```` ``` ````)
  and `plan/SKILL.md` 73–139 (```` ```` ````), and the `awk` extractions in step 3 pick
  exactly those blocks (no other `markdown` fence, no inner triple fence in the SPEC
  block); the Polish snapshot lists every heading of both templates; `workflow_config`
  `validate`/`load_sections` and the existing `({"language": 7}, …)` case support the
  AC15 design; `test_readme_has_no_polish_even_in_code` exists and narrowing it is needed
  for AC7; the contract identity test, the "no README in the contract" rule, the
  configuration-block test (unaffected by a new `## Język` section), the closing-step
  prefixes and the init `step(n)` helper (indented questions do not match `\n1. `) all
  hold under the planned edits; `test_no_domain_references` does not scan templates for
  `docs/ROADMAP.md`, and the new init text must keep `docs/ROADMAP.md` inside step 4
  (existing test, named in step 8).
- Conventions and decisions: no runtime or dev dependency, no data migration (the
  default flip is accepted in the SPEC's owner decisions); the README keeps Polish only
  in code spans (2026-09-21 row); skills stay Polish (2026-09-17/21 rows); eval policy of
  2026-09-22 followed; tests before code in steps 1–3.
- Order: no forward dependency — the map parser (step 2) precedes the template tests
  (step 3), the templates exist before the skills stop carrying them (step 5), the
  `init` template renames (step 7) keep `test_init_skill.py` green until step 8.
- Language of this plan: English, matching `"language": "en"`.
- Owner summary: dependency and migration flags true; one manual scenario (the canary).

The plan is ready: no blocker remains, the fixes stay inside the plan, and nothing in it
needs an owner decision the SPEC does not already give.

## Deviations

- **D1 — step 5, templates stay inline (owner decision C, 2026-09-23).** `idea` and `plan`
  do not `cat` their template; `## Szablon SPEC.md` / `## Szablon PLAN.md` keep the template
  as two fenced blocks, `### Polski (\`pl\`)` and `### Angielski (\`en\`)`, chosen by
  `language` (`en` for a missing or unsupported value). The planned
  `test_idea_and_plan_read_their_template_through_the_shell` became
  `test_idea_and_plan_carry_their_templates_pinned_to_the_files`: each inline block equals
  `templates/<DOC>.<language>.md` byte for byte, the skill has exactly two `markdown`
  blocks, and the choice paragraph names `language` and both template files. The
  `plugin/README.md` section map gained one sentence saying so. Rationale: the step 5 probe
  (Results) — a headless stage subagent is refused the read.

## Final review

### 2026-09-23 — /pipeline:final-review (report)

Three independent perspectives (SPEC/PLAN compliance, quality, tests), each finding checked
in the code. `bash scripts/check.sh` green (1714 passed). The Polish SPEC/PLAN templates are
byte-identical to the inline blocks on `origin/main`; the Polish `init` templates are pure
renames except `CONVENTIONS.pl.md` → `## Język` (AC14).

**AC → evidence**

| AC | Evidence | Status |
|---|---|---|
| AC1 | `plugin/README.md` → `### Language contract`, three groups; `test_readme.py` | met |
| AC2 | identical `## Język` block in the 6 stage skills, contract bullet in `ship` and the 4 agents; `test_language_contract.py` (`test_the_language_block_is_identical_everywhere`, `test_every_agent_states_its_language_part`) | met |
| AC3 | `plan/SKILL.md` step 5 (SPEC not translated); `plan-review` checklist item "język" (`major`, fixed in place); `test_plan_writes_in_the_current_language`, `test_plan_review_checks_the_language` | met |
| AC4 | `final-review` apply step 3 (English conventional-commit title, body in `language`); `ship` gate in the session language | met |
| AC5 | template files exist; inline blocks pinned byte for byte (`test_idea_and_plan_carry_their_templates_pinned_to_the_files`) | met as amended by owner decision C (D1) |
| AC6 | `SPEC.en.md` / `PLAN.en.md` headings equal the AC6 list; Polish verbatim | met (see F5) |
| AC7 | README `### Section map`; both headings in skills; `test_sections_are_named_by_both_headings` | met (test weak, F3) |
| AC8 | `test_templates_language.py` parity, frontmatter, map rows, no Polish | met |
| AC9 | tokens in `final-review`, `plan-review`, `ship` gate, README, eval criteria; legacy `warto poprawić` read rule; `test_severities_are_tokens`, `test_final_review_criteria_use_the_tokens` | met |
| AC10 | `init/SKILL.md:36` language first, `en` recommended, 4 questions; `test_the_language_is_the_first_question` | met |
| AC11 | `init` step 4 picks `CLAUDE.<language>.md`, `docs/<NAZWA>.<language>.md`; `test_init_templates.py` | met |
| AC12 | `init/SKILL.md:56` argument or `en`, no `TODO:`; eval ledger 5/5 | met (see F1) |
| AC13 | `init` steps 6–7 | met (see F1, test weak F4) |
| AC14 | `templates/docs/CONVENTIONS.{pl,en}.md` language section | met |
| AC15 | `workflow_config.py` `LANGUAGES`, default `en`, exact warning; `test_workflow_config.py`; README row | met (see F2) |
| AC16 | `plugin/evals/init-writes-the-chosen-language/`, `init-without-questions` criterion 5; ledger 5/5 both | met |
| AC17 | hard-coded `POLISH_SNAPSHOT`, `test_polish_templates_match_the_snapshot`, matches `origin/main` | met |
| AC18 | canary checklist in "After gate 2" | pending apply |
| AC19 | ROADMAP Stage 8 rewritten and 0.5.0 ticked; 4 DECISIONS rows; CONVENTIONS | met |
| AC20 | `plugin.json` 0.5.0; CHANGELOG `## 0.5.0` names the three consumer impacts | met |
| AC21 | stdlib only, `test_no_domain_references` green, check.sh green; eval receipt as last commit | pending apply |

Plan steps 1–11 ticked with reason; D1 justified by the probe and owner decision C;
nothing out of scope on the branch.

**Findings**

- **F1 `worth-fixing`** — `plugin/skills/init/SKILL.md:36`, `:56`. A re-run in a project
  with `"language": "pl"`: interactively the question still recommends `en`, so accepting
  the recommendation flips the project to English (the AC13 path, unintended); unattended,
  the fallback is `en` whatever the key says, so a missing document is generated from the
  English template inside a Polish project ("no mixing of languages"). Fix: when
  `.claude/workflow.json` already has a supported `language`, recommend it and use it as the
  unattended fallback; `en` only when the key is missing; a test on steps 2–3.
- **F2 `worth-fixing`** — `plugin/bin/workflow_metrics.py:196` (`configured_specs_dir` uses
  the strict `workflow_config.load`). A consumer with a string `language` valid before
  0.5.0 (`"EN"`, `"polski"`) → `workflow_metrics.py` without arguments exits 1 with
  `` `language` has to be one of: en, pl `` instead of the promised "warns and falls back to
  `en`" (README configuration table, CHANGELOG 0.5.0). Fix: read the config through
  `load_sections` there and print the problems as warnings, as `--format-for` does; a test.
- **F3 `worth-fixing`** — `plugin/tests/test_language_contract.py:165`. `flat =
  normalise(text)` searches the whole skill, including the inline English template, which
  holds every English heading → for `idea` and `plan` the both-headings check can never
  fail (removing `` (`## Read context`) `` from idea's prose stays green). Fix:
  `flat = normalise(without_fences(text))` (all current twins sit outside fences).
- **F4 `worth-fixing`** — `plugin/tests/test_init_skill.py:194`. The AC13 test asserts only
  `` `language` `` in step 6; deleting "istniejących dokumentów nie tłumaczysz…" and the
  step 7 notice keeps it green. Fix: assert the no-translation sentence in step 6 and the
  "dotychczasowym języku" bullet in step 7.
- **F5 `nit`** — `plugin/tests/test_templates_language.py:13`. No snapshot pins the English
  SPEC/PLAN headings or the non-heading map literals (`**Główne ryzyka:**`,
  `Weryfikacja automatyczna:`): a coordinated rename in template, inline block and map
  stays green although specs 001–005 would stop matching. Fix: an `ENGLISH_SNAPSHOT` and a
  pinned list of literal pairs.
- **F6 `nit`** — `plugin/templates/workflow.example.json:31` still shows `"language": "pl"`
  while the default is `en`. Fix: `"en"`.
- **F7 `nit`** — `plugin/skills/init/SKILL.md:54-55`. The unattended TODO example is Polish
  (`"TODO: komenda pełnej weryfikacji"`) → likely copied verbatim into an `en` project's
  `workflow.json`. Fix: `"TODO: <verify command>"` or "TODO text in `language`".
- **F8 `nit`** — `plugin/evals/final-review-ignores-false-positive/graders/criteria.md:27`
  is 103 characters (limit 100). Fix: reflow.
- **F9 `nit`** — `plugin/skills/ship/SKILL.md:137` dictates the Polish literal „brak
  znalezisk" for PLAN.md regardless of `language`. Fix: "record that there are no findings,
  in `language`".
- **F10 `nit`** — this PLAN, Owner summary → "Main risks" still describes stages `cat`ing
  templates at run time, superseded by D1. Fix: half a sentence pointing to decision C.
- **F11 `nit`** — `plugin/tests/test_language_contract.py:8-9`. `STAGE_SKILLS` / `AGENTS`
  hard-coded → a new stage skill or agent without the language block passes. Fix: derive
  from `skills/*/SKILL.md` (minus `init`) and `agents/*.md` and assert equality.
- **F12 `nit`** — `plugin/tests/test_readme.py:190` `strip_code` toggles on fences, so an
  unclosed fence hides the rest of an English template from the Polish-letter check. Fix:
  check the English templates without stripping code (they have no Polish even in code),
  or assert balanced fences.
- **F13 `nit`** — `plugin/tests/test_readme.py` `section_map` silently skips a map row
  without exactly 4 cells, dropping it from every parity check. Fix: assert the cell count.

**Rejected**

- `test_language_twins_share_their_structure` compares only heading levels, not the names
  of the `init` document headings — rejected: AC11 asks only for no Polish and unchanged
  Polish templates, and no stage reads the `init` documents by heading.

### 2026-09-23 — /pipeline:final-review (apply)

Owner decision (gate 2): all thirteen findings accepted, none rejected. Applied in
`fix: address final review of 006 language-made-explicit`:

- **F1** — `init` question 1 recommends the supported `language` already in
  `.claude/workflow.json`; unattended, the fallback order is argument → existing
  `language` → `en` (steps 2–4); `test_a_re_run_keeps_the_configured_language`; CHANGELOG.
- **F2** — `configured_specs_dir` reads the config through `load_sections` and prints the
  problems as `workflow.json: …` warnings; `test_a_faulty_key_warns_and_the_report_goes_on`,
  `test_an_unsupported_language_warns_and_does_not_stop_the_report` (`EN`, `polski`),
  `test_an_unreadable_config_is_reported` (invalid JSON still exits 1); README and
  CHANGELOG say so. The former `test_a_broken_config_is_reported` (exit 1 on an unknown
  key) was replaced: an unknown key now warns, matching the hooks and the README.
- **F3** — `test_sections_are_named_by_both_headings` searches the prose outside fences;
  checked by mutation (removing `` (`## Read context`) `` from `idea` now fails).
- **F4** — the AC13 test asserts the no-translation sentence in step 6 and the step 7
  notice.
- **F5** — `ENGLISH_HEADINGS` and `MAP_SNAPSHOT` pin the English SPEC/PLAN headings and
  every literal pair of the section map.
- **F6** — `workflow.example.json` shows `"language": "en"`.
- **F7** — the unattended TODO example is `"TODO: <verify command>"`, its description in
  `language`; `test_the_todo_example_is_not_tied_to_one_language`.
- **F8** — the eval criteria line reflowed to ≤ 100 characters.
- **F9** — `ship` records "no findings" in `language`, not a Polish literal.
- **F10** — Owner summary → Main risks points to decision C / D1.
- **F11** — `test_the_lists_cover_every_stage_and_agent` derives the stage skills (minus
  `init`) and agents from the tree.
- **F12** — the English template checks (`test_templates_language.py`,
  `test_init_templates.py`) run on the unstripped text; `strip_code` asserts balanced
  fences.
- **F13** — `section_map` asserts 3 (severity) or 4 (map) cells per row.

`bash scripts/check.sh` green (1723 passed).
