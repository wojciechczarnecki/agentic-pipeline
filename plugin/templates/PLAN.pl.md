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

| AC | Kroki | Test dowodzący | Czerwony przed zmianą |
|----|-------|----------------|-----------------------|

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
