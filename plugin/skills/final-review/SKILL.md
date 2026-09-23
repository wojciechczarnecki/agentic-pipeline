---
name: final-review
description: Etap 5 pipeline'u — końcowy code review brancha feature'a (status implemented). Tryb report — trzy niezależne perspektywy jako równoległe subagenty i raport znalezisk; tryb apply — poprawki wg decyzji właściciela, otwarcie PR, zielone CI i dopiero wtedy status done.
argument-hint: <numer lub slug speca> [report|apply]
---

# /pipeline:final-review — końcowy review feature'a

Rola: recenzent końcowy. Kod powstał w innej sesji — oceniasz go świeżym okiem, z trzech
perspektyw, które nie widzą nawzajem swoich wniosków. Poprawiasz dopiero po decyzji
właściciela: to druga bramka człowieka w pipeline'ie.

Tryby: **`report`** (domyślny) i **`apply`**. W sesji samodzielnej wykonujesz oba po kolei
z pytaniem właściciela pomiędzy; w `/pipeline:ship` każdy tryb to osobne uruchomienie.

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

## Wejście / wyjście

- Wejście: `<docs.specsDir>/NNN-<slug>/` ze statusem `implemented`; branch feature'a.
- Wyjście `report`: raport w `## Final review` w PLAN.md (zacommitowany).
- Wyjście `apply`: wdrożone przyjęte poprawki, otwarty PR z zielonym CI, status speca →
  `done` (dopiero po zielonym CI).

## Tryb report

1. **Precondition** `status: implemented`. `git fetch origin`; materiał:
   `git diff --stat origin/main...HEAD` (pełny diff i pełne wersje plików czytają
   perspektywy).
2. **Trzy perspektywy — równolegle**, jako osobne subagenty (narzędzie `Agent`, wszystkie
   trzy w jednej wiadomości). Każdy dostaje: ścieżkę speca, komendę diffu, SWOJĄ
   perspektywę i format znaleziska. Nie dostaje wniosków pozostałych ani Twoich hipotez.
   - **Zgodność ze SPEC/PLAN:** dla każdego AC dowód — plik/test, który je realizuje
     (macierz AC → dowód); kroki planu odhaczone zasadnie; `## Deviations` uzasadnione;
     do brancha nie weszło nic spoza zakresu.
   - **Jakość i utrzymywalność:** skill `/code-review` na diffie (bugi, edge-case'y,
     bezpieczeństwo); do tego zgodność z `<docs.conventions>` (wzorce kodu, teksty dla
     użytkownika wyłącznie przez wskazany tam mechanizm, styl i limit długości linii)
     i spójność z istniejącymi wzorcami (paginacja, zależności, obsługa błędów,
     struktura testów).
   - **Testy:** kluczowe ścieżki i edge-case'y pokryte (błędy autoryzacji, brak zasobu,
     walidacja, puste listy, duplikaty, granice długości)? asercje konkretne — nie tylko
     kod statusu tam, gdzie liczy się treść? testy interfejsu używają tych samych kluczy
     tekstów co kod? Gdy `verify.scopes` ma zakres UI, a zmiana dotyka interfejsu — wymagaj
     w PLAN.md wpisu o `<verify.command> <zakres UI>` oraz o obejrzanych artefaktach
     wizualnych i scenariuszu przeglądowym wymaganych przez `<docs.conventions>`.
   Format znaleziska od perspektywy:
   `[blocker|worth-fixing|nit] plik:linia — scenariusz (wejście → złe zachowanie) — poprawka`.
   Wagi to tokeny pisane jako kod w każdym języku, jak klucze metryk.
3. **Scal i zweryfikuj.** Duplikaty połącz. KAŻDE znalezisko sprawdź sam w kodzie —
   fałszywe odrzuć z jednozdaniowym powodem. Ustal wagę końcową wg realnego ryzyka.
4. **Zapisz raport** w `## Final review` w PLAN.md: data; macierz AC → dowód; znaleziska
   z id `F1…Fn` (waga, plik:linia, scenariusz, poprawka); odrzucone z powodem. W bloku
   `metrics:` SPEC.md: `final_review_blockers`, `final_review_worth_fixing`,
   `final_review_nits`.
   Płaski blok `metrics:`: liczniki całkowite, czasy `%Y-%m-%dT%H:%M`; przed zgłoszeniem
   sukcesu `workflow_metrics.py --check <spec-dir>`.
   Czerwień, której nie naprawisz z własnych artefaktów = `RESULT: ESCALATE` (samodzielnie:
   STOP z pytaniem) z nazwami brakujących kluczy; nie wymyślasz wartości, której nie zmierzyłeś.
   Zacommituj (`docs: add final review of NNN <slug>`).
5. **Decyzje:**
   - sesja samodzielna → pokaż tabelę znalezisk i zapytaj właściciela (`AskUserQuestion`,
     w języku sesji; rekomendacja: przyjąć `blocker` i `worth-fixing`, odrzucić `nit`);
     decyzje zapisz w PLAN.md → `## Decyzje właściciela` (`## Owner decisions`) i przejdź
     do trybu apply;
   - `/pipeline:ship` → zakończ blokiem RESULT z tabelą znalezisk; decyzje zbierze
     orkestrator.

## Tryb apply

1. **Decyzje** weź z PLAN.md → `## Decyzje właściciela` (`## Owner decisions`; wpis
   dotyczący końcowego review).
   Brak wpisu → eskalacja, nie zgaduj.
2. **Poprawki:** wprowadź przyjęte, ponów pełną weryfikację (`<verify.command>`), dopisz
   do raportu, co poprawiono (id → zmiana). W bloku `metrics:`: `findings_accepted`,
   `findings_rejected`; znalezisko odłożone do `<docs.backlog>` liczy się jako
   `findings_rejected` (powód: „backlog"), inaczej bilans `--check` się nie zejdzie.
3. **PR** — status speca zostaje `implemented`:
   - `<docs.roadmap>` odhaczona, `<docs.decisions>` jeśli dotyczy; `<docs.backlog>`
     zaktualizowany: nowe pozycje z priorytetem i wyzwalaczem, zrealizowane usunięte,
     pozycje z zaszłym wyzwalaczem wymienione w raporcie dla właściciela;
   - commit (`fix: address final review of NNN <slug>`, a gdy bez zmian w kodzie —
     `docs: record final review of NNN <slug>`), `git push`;
   - PR już istnieje (`gh pr view --json url`, np. przy wznowieniu po eskalacji) → nie
     twórz drugiego; inaczej
     `gh pr create --base main --title "<typ>: <angielski komunikat po squashu>" --body-file <plik>`
     — tytuł PR po angielsku w formacie commita (typ + tryb rozkazujący), bo po squashu
     staje się komunikatem commita; treść PR w języku z `language`, plik treści
     w scratchpadzie; treść: cel (ze SPEC), najważniejsze zmiany, wynik
     weryfikacji, metryki speca, scenariusze ręczne do sprawdzenia przed merge'em; stopka
     zgodnie z instrukcjami sesji.
4. **Czekaj na CI** — zawsze; w repozytorium bez ochrony brancha jesteś jedyną bramką:
   `gh pr checks <nr> --watch`. Czerwony job → pętla samokorekty
   z `/pipeline:implement` (commit, push, ponowne czekanie; 4. iteracja na tym samym
   błędzie = eskalacja). Wada produktu wykryta przez test, której naprawa wykracza poza
   przyjęte decyzje → eskalacja; nigdy nie dopasowuj testu ani danych testowych do wady.
   Przy eskalacji status zostaje `implemented`, a PR nie jest zgłaszany jako gotowy do
   merge. **Test zielony dopiero po retry (flaky)** nie blokuje PR, ale nie znika: dopisz
   go do `<docs.backlog>` (nazwa testu, numer przebiegu CI, objaw, wyzwalacz)
   i wymień w raporcie. Wpis wchodzi do commita zamykającego z kroku 5 — inaczej ślad
   ginie po merge'u.
5. **Zamknięcie — dopiero przy zielonym CI:** `status: done` + wpis w `stage_history`;
   `metrics.finished_at` (`date +%Y-%m-%dT%H:%M`). Przed `done` uruchom
   `workflow_metrics.py --check <spec-dir>` — dopóki kończy się błędem, `done` nie zapada;
   czerwień nie do naprawy = `RESULT: ESCALATE`. Licznik zmierzony jako zero zapisujesz
   jako `0` — to pomiar, nie wymyślona wartość.
   Commit (`docs: close SPEC NNN <slug>`), `git push`, ponowne `gh pr checks <nr> --watch`
   — ostatni commit PR też ma mieć zielone CI. Czerwień po samym commicie statusu to
   niestabilność, nie wada: ponów przebieg (`gh run rerun <id> --failed`), statusu nie cofaj.
6. Podaj link PR, status CI i link do przebiegu z artefaktami wizualnymi
   (`gh pr checks <nr> --json name,workflow,link` — `link` prowadzi do przebiegu); gdy
   edytujesz treść PR, uwzględnij tam to samo. Merge robi właściciel.

## Guardraile

- Zielone testy ≠ poprawny kod — nie skracaj przeglądu z tego powodu.
- W trybie report nie poprawiasz niczego — raport najpierw, zmiany po decyzji.
- `done` znaczy „PR z zielonym CI czeka na merge" — nie ustawiasz go wcześniej.
- Nie zgłaszaj nitów kosmetycznych jako blockerów — waga ma odpowiadać realnemu ryzyku.
- Nie mergujesz PR (egzekwuje też strażnik komend tego pluginu).

## Handoff

- **Uruchomiony samodzielnie:** link PR + przypomnienie o scenariuszach ręcznych;
  merge squashem robi właściciel, kolejny feature zaczyna się od `/pipeline:idea`.
- **W ramach `/pipeline:ship`:** zakończ blokiem RESULT z kontraktu agenta etapu.
