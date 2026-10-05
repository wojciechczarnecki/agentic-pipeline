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
      (po odhaczeniu kroku jego linia kończy się notatką `iterations: <k>` w backtickach:
      iteracje pętli ponad pierwszą próbę, 0, gdy krok był zielony od razu)
- [ ] 2. …

## Ryzyka i pułapki

- <np. różnice bazy testowej i produkcyjnej, migracje, strefy czasowe, teksty dla
  użytkownika, autoryzacja>

## Weryfikacja end-to-end

### Automatyczna (wykonuje /pipeline:implement)

<komendy na uruchomionej aplikacji: podniesienie stacku, zapytania HTTP, skrypty, testy
przeglądowe — z oczekiwanymi wynikami>

### Ręczna (wykonuje właściciel)

- <scenariusz — tylko to, czego nie da się zautomatyzować>
  Zaliczony, gdy: <polecenie, zapytanie albo miejsce w UI, z oczekiwanym wynikiem>

## Definition of Done

- [ ] wszystkie kroki odhaczone
- [ ] `<verify.command>` w całości zielony
- [ ] weryfikacja end-to-end (automatyczna) wykonana, wynik zapisany tutaj
- [ ] `<docs.roadmap>` zaktualizowana; `<docs.decisions>` / dokumenty domenowe z mapy
      w `CLAUDE.md`, jeśli dotyczy
- [ ] status speca: `implemented`

## Decyzje właściciela

_(dopisuje /pipeline:ship lub etap przy eskalacji, jeden wpis w linii: `- YYYY-MM-DD — <etap> — `<rodzaj>` — <pytanie> — <decyzja>`, rodzaj to `decision`, `permission` albo `tooling`; wpis bramki final-review ma rodzaj `gate` i kończy się `accepted`: F1, F2; `rejected`: F3, `none` dla pustej listy)_

## Review log

_(wypełnia /pipeline:plan-review — jedna pozycja listy na ustalenie, zaczynająca się od wagi w backtickach: `- `blocker` — …`, `major` albo `minor`; bez ustaleń jedna pozycja `- `none` — brak ustaleń`)_

## Deviations

_(wypełnia /pipeline:implement — jeden wpis na odstępstwo, z uzasadnieniem: `- `minor` — …` albo `- `major` — …`)_

## Final review

_(wypełnia /pipeline:final-review — jedna linia na ustalenie: `- **F<n>** `<blocker|worth-fixing|nit>` — …`)_
