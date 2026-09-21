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

## Konfiguracja projektu

- Przeczytaj `.claude/workflow.json`; brak pliku = domyślne z README pluginu → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` itd. = wartości z tej konfiguracji (klucze w README).

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
   `[blocker|warto poprawić|nit] plik:linia — scenariusz (wejście → złe zachowanie) — poprawka`.
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
     rekomendacja: przyjąć blockery i „warto poprawić", odrzucić nity); decyzje zapisz
     w PLAN.md → `## Decyzje właściciela` i przejdź do trybu apply;
   - `/pipeline:ship` → zakończ blokiem RESULT z tabelą znalezisk; decyzje zbierze
     orkestrator.

## Tryb apply

1. **Decyzje** weź z PLAN.md → `## Decyzje właściciela` (wpis dotyczący końcowego review).
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
     `gh pr create --base main --title "<typ>: <komunikat po squashu>" --body-file <plik>`
     — plik treści w scratchpadzie; treść: cel (ze SPEC), najważniejsze zmiany, wynik
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
