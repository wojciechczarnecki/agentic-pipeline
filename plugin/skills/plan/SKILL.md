---
name: plan
description: Etap 2 pipeline'u — techniczny plan implementacji feature'a na podstawie SPEC.md (status spec-ready). Tworzy PLAN.md z krokami i dokładnymi komendami weryfikacyjnymi.
argument-hint: <numer lub slug speca, np. 001>
---

# /pipeline:plan — SPEC → plan implementacji

Rola: architekt. SPEC mówi CO i PO CO — Ty decydujesz JAK. Wynik to plan, który inny
agent wykona w świeżej sesji bez zgadywania: każdy krok ma zdefiniowany sygnał
zwrotny (dokładne komendy weryfikacyjne), bo to na nich `/pipeline:implement` opiera
pętlę samokorekty.

Plan ma dwóch czytelników: **agentów** kolejnych etapów (cała treść — szczegółowa,
jednoznaczna) i **właściciela** (tylko „Streszczenie dla właściciela" /
`## Owner summary` — czyta je przy eskalacji i przy raporcie z końcowego review, nie
zatwierdza całego planu).

## Konfiguracja projektu

- Przeczytaj `.claude/workflow.json`; brak pliku = domyślne z README pluginu → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` itd. = wartości z tej konfiguracji (klucze w README).

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

## Wejście / wyjście

- Wejście: `<docs.specsDir>/NNN-<slug>/SPEC.md` ze statusem `spec-ready`.
- Wyjście: `<docs.specsDir>/NNN-<slug>/PLAN.md` zacommitowany na branchu lane'a;
  status speca → `plan-draft`.

## Kroki

1. **Znajdź spec.** Argument wskazuje numer/slug; bez argumentu wylistuj
   `<docs.specsDir>/*/SPEC.md` ze statusem `spec-ready` i zapytaj właściciela, który brać.
2. **Precondition:** `status: spec-ready`. Inny status → STOP; wyjaśnij, którego etapu
   pipeline'u brakuje. Sprawdź branch (`git branch --show-current`): pracujesz na branchu
   lane'a `feat/NNN-<slug>`; jeśli nie istnieje (spec wszedł historycznie na `main`) —
   utwórz go: `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`
   (przy pracy równoległej: worktree w katalogu z `worktree.dir`).
3. **Zbierz kontekst:** SPEC w całości (łącznie z „Decyzje właściciela" /
   `## Owner decisions`); `<docs.conventions>`; `<docs.decisions>`; dokumenty domenowe
   z mapy dokumentów w `CLAUDE.md` projektu (według warunków w mapie); kod obszaru — pliki, które plan będzie zmieniać, czytaj W CAŁOŚCI
   (bez limit/offset). Wynotuj istniejące wzorce do reużycia z konkretnymi ścieżkami
   (np. paginacja w konkretnym module API, wspólne fixtures testowe, obsługa błędów
   w kliencie API).
4. **Zaprojektuj podejście:** minimalne, zgodne z konwencjami, pokrywające WSZYSTKIE
   AC. Tam, gdzie istnieje realny wybór, rozważ ≥2 warianty; do planu wpisz wybrany
   + jedno zdanie dlaczego.
5. **Spisz PLAN.md** według bloku szablonu dla bieżącego `language` (sekcja „Szablon
   PLAN.md"), w języku z `language` — także wtedy, gdy SPEC.md jest w innym języku (np.
   napisany przed zmianą `language`); SPEC-a nie tłumaczysz i nie zmieniasz. Kroki małe
   (≤ ~1 h pracy) i domknięte: każdy ma sekcję „Weryfikacja automatyczna"
   (`Automatic verification:`) z DOKŁADNYMI komendami (ścieżki testów,
   nie ogólnik „dodaj testy") — to jest kontrakt dla pętli samokorekty
   `/pipeline:implement`. Kolejność bez zależności „w przód"; migracja danych zawsze
   jako osobny krok. Weryfikację end-to-end rozdziel na automatyczną (wykona agent)
   i ręczną (wykona właściciel) — do ręcznej trafia tylko to, czego nie da się
   zautomatyzować. Gdy `verify.scopes` ma zakres UI, a zmiana dotyka interfejsu — zaplanuj
   w weryfikacji automatycznej `<verify.command> <zakres UI>` oraz OBEJRZENIE artefaktów
   wizualnych i aktualizację scenariusza przeglądowego wymaganych przez `<docs.conventions>`.
6. **Macierz AC → kroki:** każde AC musi mieć kroki, które je realizują, i test, który
   je dowodzi. AC niemożliwe do pokrycia → eskalacja (luka w SPEC); nie łataj SPEC
   samodzielnie.
7. **Streszczenie dla właściciela** (`## Owner summary`) wypełnij na końcu, gdy plan
   jest gotowy. Flagi „nowa zależność" i „migracja danych" muszą być prawdziwe — od nich
   zależy, czy recenzja planu może go zatwierdzić bez właściciela.
8. **Zamknięcie etapu:** w SPEC.md `status: plan-draft` + wpis w `stage_history`; w bloku
   `metrics:` ustaw `started_at` i `escalations: 0` (jeśli brak; `date +%Y-%m-%dT%H:%M`)
   oraz `plan_steps`.
   Płaski blok `metrics:`: liczniki całkowite, czasy `%Y-%m-%dT%H:%M`; przed zgłoszeniem
   sukcesu `workflow_metrics.py --check <spec-dir>`.
   Czerwień, której nie naprawisz z własnych artefaktów = `RESULT: ESCALATE` (samodzielnie:
   STOP z pytaniem) z nazwami brakujących kluczy; nie wymyślasz wartości, której nie zmierzyłeś.
   Zacommituj (`docs: add PLAN NNN <slug>`). NIE implementuj niczego.

## Szablon PLAN.md

Blok wybierasz według bieżącego `language` — nie według języka SPEC: `pl` → „Polski
(`pl`)"; `en`, brak klucza albo wartość spoza `en`/`pl` → „Angielski (`en`)". Szablonu nie
tłumaczysz i nie łączysz bloków — PLAN ma dokładnie nagłówki wybranego bloku. Bloki są
wierną kopią `templates/PLAN.pl.md` i `templates/PLAN.en.md` pluginu (pilnuje tego test);
nie czytasz tych plików w trakcie pracy.

### Polski (`pl`)

````markdown
# PLAN NNN — <nazwa feature'a>

## Streszczenie dla właściciela

- **Podejście:** <2–4 zdania>
- **Główne ryzyka:** <…>
- **Nowa zależność:** nie | tak — <nazwa, po co; czy zaakceptowana w SPEC → „Decyzje właściciela">
- **Migracja danych:** nie | tak — <co zmienia; czy zaakceptowana w SPEC → „Decyzje właściciela">
- **Scenariusze ręczne dla właściciela:** <liczba + jednym zdaniem, co obejmują>

## Podejście

<jak i dlaczego tak; istniejące wzorce/utilsy do reużycia ze ścieżkami plików>

## Macierz AC → kroki

| AC | Kroki | Test dowodzący |
|----|-------|----------------|

## Kroki

- [ ] 1. <co> — pliki: `…`
      Weryfikacja automatyczna: `<dokładne komendy, np. uruchomienie konkretnego pliku testów>`
- [ ] 2. …

## Ryzyka i pułapki

- <np. różnice bazy testowej i produkcyjnej, migracje, strefy czasowe, teksty dla
  użytkownika, autoryzacja>

## Weryfikacja end-to-end

### Automatyczna (wykonuje /pipeline:implement)

<komendy na uruchomionej aplikacji: podniesienie stacku, zapytania HTTP, skrypty, testy
przeglądowe — z oczekiwanymi wynikami>

### Ręczna (wykonuje właściciel)

<krótka lista scenariuszy — tylko to, czego nie da się zautomatyzować>

## Definition of Done

- [ ] wszystkie kroki odhaczone
- [ ] `<verify.command>` w całości zielony
- [ ] weryfikacja end-to-end (automatyczna) wykonana, wynik zapisany tutaj
- [ ] `<docs.roadmap>` zaktualizowana; `<docs.decisions>` / dokumenty domenowe z mapy
      w `CLAUDE.md`, jeśli dotyczy
- [ ] status speca: `implemented`

## Decyzje właściciela

_(dopisuje /pipeline:ship lub etap przy eskalacji: data, etap, pytanie, decyzja)_

## Review log

_(wypełnia /pipeline:plan-review)_

## Deviations

_(wypełnia /pipeline:implement — każde odstępstwo od planu z uzasadnieniem)_

## Final review

_(wypełnia /pipeline:final-review)_
````

### Angielski (`en`)

````markdown
# PLAN NNN — <feature name>

## Owner summary

- **Approach:** <2–4 sentences>
- **Main risks:** <…>
- **New dependency:** no | yes — <name, what for; accepted in SPEC → "Owner decisions"?>
- **Data migration:** no | yes — <what it changes; accepted in SPEC → "Owner decisions"?>
- **Manual scenarios for the owner:** <a number + one sentence on what they cover>

## Approach

<how and why; existing patterns/utilities to reuse, with file paths>

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|

## Steps

- [ ] 1. <what> — files: `…`
      Automatic verification: `<exact commands, e.g. running a specific test file>`
- [ ] 2. …

## Risks and traps

- <e.g. test vs production database differences, migrations, time zones, user-facing
  texts, authorisation>

## End-to-end verification

### Automatic (performed by /pipeline:implement)

<commands against the running application: bringing the stack up, HTTP requests, scripts,
visual review tests — with the expected results>

### Manual (performed by the owner)

<a short list of scenarios — only what cannot be automated>

## Definition of Done

- [ ] all steps ticked
- [ ] `<verify.command>` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `<docs.roadmap>` updated; `<docs.decisions>` / domain documents from the map
      in `CLAUDE.md`, if applicable
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

_(filled in by /pipeline:plan-review)_

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
````

## Guardraile

- Nie zmieniaj treści SPEC (poza polem `status`, `stage_history` i blokiem `metrics`).
- Nie dodawaj zakresu ponad SPEC (gold-plating) — pomysły „przy okazji" zapisuj
  jako propozycje do `<docs.backlog>` w podsumowaniu etapu, nie jako kroki planu.
- Kod w planie tylko tam, gdzie precyzja tego wymaga (sygnatury, kształt schematu) —
  plan to nie implementacja.

## Handoff

- **Uruchomiony samodzielnie:** plan gotowy (status `plan-draft`); następny etap to
  `/pipeline:plan-review NNN` po `/clear` — recenzent ma ocenić plan świeżym okiem.
- **W ramach `/pipeline:ship`:** zakończ blokiem RESULT z kontraktu agenta etapu.
