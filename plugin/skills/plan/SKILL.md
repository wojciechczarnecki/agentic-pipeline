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
  Sekcję wskazujesz oboma nagłówkami i przyjmujesz którykolwiek (mapa sekcji — sekcja
  „Mapa sekcji").
- Zawsze po angielsku, niezależnie od `language` i sesji: komunikaty commitów, tytuły PR,
  nazwy branchy i slugi speców, klucze bloku `RESULT`, klucze metryk i tokeny wag.
- Rozmowa z właścicielem — pytania, eskalacje, podsumowania i handoff — w języku sesji
  Claude Code, nigdy według `language`.

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
5. **Spisz PLAN.md** według szablonu wczytanego dla bieżącego `language` (sekcja
   „Szablon PLAN.md"), w języku z `language` — także wtedy, gdy SPEC.md jest w innym języku (np.
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

Szablon wczytujesz narzędziem `Read` — jeden plik, wybrany według bieżącego `language`,
nie według języka SPEC:

- `pl` → `${CLAUDE_PLUGIN_ROOT}/templates/PLAN.pl.md`;
- `en`, brak klucza albo inna wartość → `${CLAUDE_PLUGIN_ROOT}/templates/PLAN.en.md`.

Wczytujesz tylko ten jeden plik. Szablonu nie tłumaczysz i nie łączysz z drugim — PLAN ma
dokładnie jego nagłówki. Nieudany odczyt szablonu → postępujesz według sekcji „Mapa
sekcji" (stop z komunikatem; szablonu nie odtwarzasz z pamięci).

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
