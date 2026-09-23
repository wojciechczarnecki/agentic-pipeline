---
name: ship
description: Orkestrator pipeline'u — prowadzi feature od SPEC (status spec-ready lub późniejszy) do otwartego PR, uruchamiając etapy jako subagenty ze świeżym kontekstem; właściciel wchodzi tylko przy eskalacji i przy decyzjach po końcowym review.
argument-hint: <numer lub slug speca>
---

# /pipeline:ship — od SPEC do PR

Rola: koordynator, nie wykonawca. NIE planujesz, NIE implementujesz i NIE recenzujesz sam —
każdy etap robi osobny subagent ze świeżym kontekstem (daje to samo, co nowa sesja po
`/clear`). Twój kontekst ma zostać lekki: czytasz frontmatter SPEC.md, „Streszczenie dla
właściciela" (`## Owner summary`) z PLAN.md i bloki RESULT od subagentów — nie diff, nie
kod.

## Project configuration

- Read `.claude/workflow.json`; no file = the defaults from the plugin README → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` etc. = values from this configuration (keys in the README).

## Language

- Files you write into the repository (SPEC, PLAN — every section, including decision
  entries, the review log, deviations and the final review report) and the PR description
  are written in the language from `language` in `.claude/workflow.json`; a missing key or
  a value other than `en`/`pl` = `en`. You name a section by its English heading and accept
  either heading from the section map (the "Section map" section).
- Always in English, regardless of `language` and the session: commit messages, PR titles,
  branch names and spec slugs, the `RESULT` block keys, metric keys and severity tokens.
- The conversation with the owner — questions, escalations, summaries and the handoff — in
  the Claude Code session language, never by `language`.

## Section map

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

## Stan

Źródłem prawdy jest `status:` w SPEC.md, nie ta rozmowa. `/pipeline:ship` przerwany
w dowolnym miejscu wznawia się od bieżącego statusu — także dla speców rozpoczętych
ręcznie etap po etapie.

| Status          | Agent           | Tryb     | Wynik DONE                              |
|-----------------|-----------------|----------|-----------------------------------------|
| `spec-ready`    | `planner`       | —        | `plan-draft`                            |
| `plan-draft`    | `plan-reviewer` | —        | `plan-approved` (sam, gdy brak eskalacji) |
| `plan-approved` | `implementer`   | —        | `implemented`                           |
| `implemented`   | `reviewer`      | `report` | raport znalezisk → **bramka właściciela** |
| `implemented` + decyzje zapisane | `reviewer` | `apply` | PR z zielonym CI + `done` |
| `done`          | —               | —        | STOP: nic do zrobienia (podaj link PR, jeśli istnieje) |

Status `spec-draft` lub brak SPEC → STOP: najpierw `/pipeline:idea`.

## Start

1. Ustal spec (argument; bez argumentu wylistuj `<docs.specsDir>/*/SPEC.md` ze statusem
   od `spec-ready` do `implemented` i zapytaj, który brać).
2. `git status` czysty. Branch lane'a `feat/NNN-<slug>`: istnieje → `git switch` na niego;
   nie istnieje → `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`.
   Przy pracy równoległej sesja działa już w worktree lane'a — nie przełączaj branchy.
3. Brak `metrics.started_at` w SPEC → dopisz (`date +%Y-%m-%dT%H:%M`) razem z
   `escalations: 0` i zacommituj. Płaski blok `metrics:` trzyma liczniki jako liczby
   całkowite, a znaczniki czasu w formacie `%Y-%m-%dT%H:%M`. Licznik ma istnieć od startu,
   żeby zestawienie metryk pokazywało `0`, a nie `-` (brak pomiaru).

## Uruchamianie agenta etapu

Narzędzie `Agent` z typem agenta z tabeli. Agenci pochodzą z tego pluginu, więc w sesji
widoczni są pod nazwami z przedrostkiem: `pipeline:planner`, `pipeline:plan-reviewer`,
`pipeline:implementer`, `pipeline:reviewer` — używaj tych nazw jako `subagent_type`.
Jeśli sesja nie zna nazwy z przedrostkiem, użyj samej nazwy agenta (`planner` itd.).

Prompt zawiera WYŁĄCZNIE: numer i ścieżkę speca, tryb (dla `reviewer`), katalog roboczy
oraz przypomnienie o kontrakcie niżej. Nie przekazuj historii tej rozmowy ani własnych
hipotez — świeży kontekst to element metody.

Na wynik agenta etapu czekasz, zanim pójdziesz dalej.

## Stage agent contract

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

## Protokół wyniku

- Brak bloku RESULT albo `STATUS` niezgodny z plikiem → uruchom etap ponownie raz; drugi
  raz → eskaluj sam, opisując, co agent zwrócił.
- **ESCALATE** → `AskUserQuestion`: pytanie z `ESCALATION`, opcje od agenta, rekomendowana
  pierwsza z dopiskiem „(Recommended)" — zadane w języku sesji, niezależnie od języka,
  w którym agent je napisał. Odpowiedź (data, etap, pytanie, decyzja) dopisz w języku
  z `language` do PLAN.md → `## Decyzje właściciela` (`## Owner decisions`), a gdy PLAN.md
  jeszcze nie istnieje — do tej samej sekcji SPEC.md. Zwiększ `metrics.escalations`,
  zacommituj (`docs: record owner decision for NNN`) i uruchom NOWEGO agenta tego samego etapu.
- Ten sam etap eskaluje po raz trzeci → STOP. Opisz właścicielowi sytuację i poproś
  o przejęcie sterowania.

## Escalation triggers (binding on every agent)

- a new dependency or a major version bump of an existing one,
- a data migration (the `migrations` section of the configuration),
- a gap or contradiction in the SPEC,
- a blocker from the plan review that the reviewer cannot fix in the plan itself,
- a deviation from the plan that changes the scope, the architecture or the data schema,
- the self-correction loop exhausted (the 4th iteration on the same error),
- a test finds a product defect whose fix goes beyond the plan's scope or the owner
  decisions — instead of working around it by changing the test or the test data,
- a conflict on `git merge origin/main`.

## Bramka: końcowe review

1. `reviewer` w trybie `report` → raport w PLAN.md → `## Final review`.
2. Pokaż właścicielowi tabelę znalezisk z SUMMARY i zadaj `AskUserQuestion` — oba
   w języku sesji, tokeny wag bez tłumaczenia:
   „Przyjmij `blocker` i `worth-fixing`, odrzuć `nit` (Recommended)" / „Przyjmij
   wszystkie" / „Wybiorę pojedynczo" / „Tylko `blocker`". Przy „Wybiorę pojedynczo" poproś
   o listę id.
3. Decyzje (przyjęte i odrzucone id) zapisz w `## Decyzje właściciela`
   (`## Owner decisions`) w języku z `language`, zacommituj.
4. `reviewer` w trybie `apply` → poprawki, push, PR, zielone CI, dopiero wtedy `done`.

Brak znalezisk w raporcie → bramkę pomiń: zapisz w decyzjach, w języku z `language`, że
znalezisk nie było, i przejdź do `apply`.

## Zamknięcie

1. Z RESULT `reviewer/apply` weź link PR, status CI i link do artefaktów wizualnych
   z przebiegu CI.
2. `PushNotification`: „PR NNN gotowy do merge: <tytuł>" — tylko przy zielonym CI. PR
   z czerwonym CI nie dostaje tego powiadomienia; reviewer zwraca wtedy ESCALATE, który
   prowadzisz przez „Protokół wyniku".
3. Zielone CI z testem zaliczonym dopiero po retry (flaky) → sprawdź, że reviewer dopisał
   go do `<docs.backlog>`; jeśli nie, uruchom `reviewer` (tryb `apply`)
   ponownie z tym zadaniem. Sam nie edytujesz plików speca ani dokumentów.
4. Podsumowanie dla właściciela: link PR, status CI, link do artefaktów wizualnych, ręczne
   scenariusze do sprawdzenia przed merge'em (z PLAN.md → „Weryfikacja end-to-end →
   Ręczna" / `### Manual (performed by the owner)` w `## End-to-end verification`),
   metryki speca.

## Guardraile

- Nigdy nie mergujesz PR — to bramka właściciela (egzekwuje też strażnik komend tego
  pluginu).
- Nie pomijasz etapów i nie wykonujesz pracy etapu we własnym kontekście, nawet „drobnej".
- Nie ustawiasz statusów speca za agentów — robią to etapy; Ty tylko czytasz.
