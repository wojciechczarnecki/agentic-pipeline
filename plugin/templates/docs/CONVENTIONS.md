# Konwencje rozwoju

Obowiązujące konwencje kodu i procesu. Skrót żelaznych zasad jest w CLAUDE.md;
ten dokument jest źródłem szczegółów.

## Język

- Kod, identyfikatory, komentarze i komunikaty commitów: TODO
- Dokumentacja (`docs/`, `specs/`): TODO (to samo, co `language` w `.claude/workflow.json`)
- Nie mieszamy języków w obrębie jednego dokumentu.

## Styl kodu

- Line length: TODO
- Formatowanie i lint: TODO (te same komendy co w `format[]` w `.claude/workflow.json`)
- Bez docstringów; kod samodokumentujący się.
- Komentarze tylko tam, gdzie kod nie może wyrazić ograniczenia.

## Teksty widoczne dla użytkownika

TODO: jedno miejsce na napisy (plik/moduł), zasada kluczy, jak używają ich testy.

## Testy

**Każdy nowy feature MUSI mieć testy.**

- TODO: gdzie leżą testy poszczególnych warstw i czym są uruchamiane
- Pisz testy PRZED lub RAZEM z implementacją.
- Minimalne pokrycie: kluczowe ścieżki + edge case'y (błędy autoryzacji, brak zasobu,
  walidacja, puste listy, duplikaty, granice zakresów).
- Asercje konkretne: tam, gdzie liczy się treść odpowiedzi, sprawdzaj treść.
- Pełna weryfikacja stacku jednym poleceniem: TODO (`verify.command`).

### Testy interfejsu

TODO: jak uruchomić zakres UI (`verify.scopes`), gdzie lądują artefakty wizualne i które
widoki są obowiązkowe do obejrzenia przy zmianie ekranu.

## Commity i branche

- Typy commitów: `feat` / `fix` / `test` / `docs` / `refactor` / `chore`
- Treść w trybie rozkazującym (`add`, `fix`, `harden`).
- Branch per zadanie: `feat/NNN-<slug>`, `fix/...`, `chore/...`, `docs/...`
- PR do `main` merguj przez **squash**; CI musi być zielone przed merge.
- Commity agenta: po każdym zielonym kroku, tylko pliki tego kroku.
- Aktualizacja brancha: `git merge origin/main`, nie rebase.

## Praca równoległa

Każdy lane dostaje własny branch i własny katalog roboczy (git worktree) w katalogu
z `worktree.dir`. Numer speca agent bierze jako pierwszy wolny łącznie w katalogu speców,
nazwach branchy i worktree.

## Metryki workflow

Każdy spec niesie w frontmatterze SPEC.md płaski blok `metrics:`, wypełniany przez etapy
pipeline'u. Format kluczy i zestawienie: README pluginu `pipeline`
(`workflow_metrics.py [katalog-speców]`, `workflow_metrics.py --check <katalog-speca>` —
przez `PATH`, na który Claude Code dopisuje `bin/` pluginu).

## Zależności

- TODO: zamrażanie wersji, pliki lock, kanał aktualizacji (Dependabot), polityka major.
