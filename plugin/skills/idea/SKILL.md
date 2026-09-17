---
name: idea
description: Etap 1 pipeline'u — krytyczny review pomysłu na feature i spisanie SPEC.md w katalogu speców. Użyj, gdy właściciel podaje koncepcję nowego feature'a albo wskazuje pozycję z roadmapy do przygotowania.
argument-hint: <opis feature'a lub pozycja z roadmapy>
---

# /pipeline:idea — review pomysłu → SPEC

Jesteś krytycznym partnerem projektowym właściciela, nie stenografem. Twoim zadaniem
NIE jest spisanie pomysłu, tylko najpierw jego sprawdzenie: konfrontacja z istniejącym
kodem, decyzjami i roadmapą, wykrycie dziur i doprowadzenie — w dialogu z właścicielem
— do spójnej, kompletnej koncepcji. Dopiero ona trafia do SPEC.md. Każde pytanie,
które zadajesz, to pytanie, na które kod i dokumenty nie odpowiadają — pokaż, że
najpierw sprawdziłeś.

To jedyny etap pipeline'u prowadzony w dialogu: zatwierdzony SPEC jest pierwszą bramką
właściciela, a dalsze etapy (`/pipeline:ship`) biegną autonomicznie na jego podstawie.
Luka w SPEC wraca potem jako eskalacja — tańsza jest tutaj.

## Konfiguracja projektu

Zanim cokolwiek ocenisz, przeczytaj `.claude/workflow.json` — to jedyne miejsce, w którym
projekt opisuje sam siebie: ścieżki dokumentów (`docs.roadmap`, `docs.project`,
`docs.decisions`, `docs.conventions`, `docs.backlog`), katalog speców (`docs.specsDir`),
komenda pełnej weryfikacji i jej zakresy (`verify.command`, `verify.scopes`), katalog
worktree, produkcja poza zasięgiem agenta, katalog hooków gita i język dokumentów
(`language`). Brak pliku = wartości domyślne opisane w README pluginu; wtedy zaproponuj
właścicielowi `/pipeline:init`. Dalej `<docs.roadmap>`, `<docs.specsDir>` itd. oznaczają
wartości z tej konfiguracji.

## Wejście / wyjście

- Wejście: opis feature'a od właściciela lub pozycja z `<docs.roadmap>`.
- Wyjście: `<docs.specsDir>/NNN-<slug>/SPEC.md` ze statusem `spec-ready`, zacommitowany
  na branchu lane'a (NNN = pierwszy wolny numer, zawsze ustalany automatycznie — skan
  `<docs.specsDir>`, nazw branchy i worktree; slug po angielsku, kebab-case).

## Kroki

1. **Zbierz kontekst (zanim cokolwiek ocenisz):**
   Gotowy zakres lub wymagania w prompcie nie zwalniają ze zbierania kontekstu —
   dokumenty mogą je zmienić.
   - `<docs.roadmap>` — gdzie feature leży w planie, co go poprzedza lub blokuje;
   - `<docs.project>` — wymagania funkcjonalne, których dotyka;
   - `<docs.decisions>` — decyzje, z którymi pomysł może kolidować;
   - dokumenty domenowe z mapy dokumentów w `CLAUDE.md` projektu — według warunków
     podanych w mapie; dokument domenowy to każdy wiersz tej mapy spoza ścieżek `docs.*`
     konfiguracji i spoza katalogu speców;
   - istniejący kod, który feature zmieni lub rozszerzy — wskazane pliki czytaj
     W CAŁOŚCI (Grep/Read po konkretach, nie domysłach).

   Sposób lektury dokumentów jest dowolny (pełna albo celowane wyszukiwanie), ale
   `<docs.roadmap>`, `<docs.project>`, `<docs.decisions>` i każdy dokument domenowy
   trafiają do sekcji „Przeczytany kontekst" w SPEC.
2. **Skonfrontuj pomysł.** Oceń po kolei:
   - cel — czy wiadomo, jaki problem użytkownika rozwiązujemy i po czym poznamy sukces;
   - zakres — czy nie za szeroki na jeden feature; co wyciąć do osobnego speca;
   - kolizje — z `<docs.decisions>`, z istniejącym interfejsem, schematami i danymi;
   - edge-case'y i stany błędów;
   - przekroje: uprawnienia i role, walidacja, teksty widoczne dla użytkownika,
     migracje danych, wymogi prawne dotyczące przetwarzanych danych, testowalność.
3. **Pytaj właściciela rundami** (`AskUserQuestion`, max 4 pytania na rundę — limit
   narzędzia; rund dowolnie wiele). Dyscyplina pytań:
   - najpierw te, które najbardziej zmieniają kształt speca;
   - nie pytaj o nic, co rozstrzyga kod lub dokument;
   - ZAWSZE rekomenduj — każde pytanie ma wskazaną opcję rekomendowaną: pierwsza
     w liście, z dopiskiem „(Recommended)" w ETYKIECIE opcji (nie w opisie — inaczej
     UI tego nie pokaże), a w treści pytania lub preambule jedno zdanie DLACZEGO ją
     rekomendujesz. Nigdy nie zostawiaj właścicielowi samego neutralnego zestawu opcji
     bez rekomendacji i jej powodu — on potwierdza albo nadpisuje. Gdy trafniejsza
     jest rekomendacja łącząca/rozdzielająca opcje (np. „A dla X, B dla Y"), wyłóż to
     w preambule zamiast na siłę wskazywać jedną opcję;
   - korektę właściciela sprzeczną z tym, co widziałeś w kodzie, ZWERYFIKUJ w kodzie,
     zanim ją przyjmiesz — mógł opisać stan życzeniowy, nie faktyczny;
   - zapytaj wprost o to, co później byłoby eskalacją: czy feature wymaga nowej
     zależności lub migracji danych — i czy właściciel akceptuje je z góry.
   Iteruj, aż znikną luki blokujące.
4. **Spisz SPEC.md** według szablonu (utwórz katalog `<docs.specsDir>/NNN-<slug>/`),
   w języku z `language`. Zanim zapiszesz pierwszy plik — utwórz branch lane'a:
   `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`;
   przy zadeklarowanej pracy równoległej zamiast tego utwórz worktree w katalogu
   z `worktree.dir` i wszystkie pliki lane'a twórz w jego katalogu.
   Wymaganie, którego nie potwierdził ani właściciel, ani kod (wywnioskowane przez
   Ciebie), oznacz dopiskiem `(założenie)` — to najczęstsze źródło błędów speca.
   Zgody udzielone z góry (zależność, migracja) zapisz w sekcji „Decyzje właściciela".
5. **Przedstaw właścicielowi** zwięzłe podsumowanie, decyzje podjęte po drodze oraz
   OSOBNO listę wszystkich pozycji `(założenie)` do zatwierdzenia lub odrzucenia.
   Po jego akceptacji usuń dopiski przy zatwierdzonych, ustaw `status: spec-ready`,
   dopisz wpis do `stage_history` i zacommituj (`docs: add SPEC NNN <slug>`).
6. Jeśli po drodze zapadła decyzja o trwałym znaczeniu architektonicznym — dopisz ją
   też do `<docs.decisions>` (w tym samym commicie).

## Szablon SPEC.md

```markdown
---
status: spec-draft
stage_history:
  - "spec-draft — YYYY-MM-DD"
---

# SPEC NNN — <nazwa feature'a>

## Cel

<1–3 zdania: jaki problem użytkownika rozwiązujemy i po czym poznamy, że działa>

## Kontekst

<powiązane feature'y/specy; stan istniejącego kodu w tym obszarze (ścieżki plików);
pozycja w roadmapie i wiążące decyzje trafiają do „Przeczytany kontekst">

## Przeczytany kontekst

- `<docs.roadmap>` — <co wynika dla feature'a albo dlaczego nie dotyczy>
- `<docs.project>` — <co wynika dla feature'a albo dlaczego nie dotyczy>
- `<docs.decisions>` — <co wynika dla feature'a albo dlaczego nie dotyczy>
- `<dokument domenowy z mapy w CLAUDE.md>` — <co wynika dla feature'a albo dlaczego nie
  dotyczy> (jedna pozycja na dokument domenowy w rozumieniu kroku 1)

## Zakres

- <konkretna pozycja>

## Poza zakresem

- <co świadomie odpuszczamy + gdzie to trafia (backlog z priorytetem i wyzwalaczem / przyszły spec)>

## Wymagania i kryteria akceptacji

- [ ] AC1: <sprawdzalne kryterium — obserwowalne zachowanie, nie implementacja>
- [ ] AC2: <…> (założenie)   <- dopisek przy AC niepotwierdzonych przez właściciela/kod

## Decyzje i odrzucone alternatywy

| Decyzja | Odrzucone alternatywy | Uzasadnienie |
|---------|-----------------------|--------------|

## Decyzje właściciela

- <zgody udzielone z góry, np. „nowa zależność X — zaakceptowana"; lub „brak">

## Pytania otwarte (nieblokujące)

- <lub „brak">
```

## Guardraile

- NIE projektuj implementacji (pliki, funkcje, kroki) — to rola `/pipeline:plan`.
- SPEC ze statusem `spec-ready` nie może zawierać pytań blokujących ani
  niezatwierdzonych `(założenie)` — sekcja „Pytania otwarte" jest wyłącznie na
  kwestie nieblokujące.
- SPEC ze statusem `spec-ready` ma w sekcji „Przeczytany kontekst" pozycję dla
  `<docs.roadmap>`, `<docs.project>`, `<docs.decisions>` i każdego dokumentu domenowego
  z mapy w `CLAUDE.md` (definicja w kroku 1).
- Każde AC musi być sprawdzalne: da się napisać test albo procedurę ręczną, która
  je potwierdza. „Obsługuje długie teksty" to nie AC; „tekst >10 000 znaków → 422" tak.
- W `<docs.roadmap>` możesz jedynie dopisać odnośnik do speca przy realizowanej pozycji —
  nic więcej.

## Handoff

Powiedz właścicielowi: SPEC gotowy i zacommitowany; następny krok to `/pipeline:ship NNN`
po `/clear` (albo w nowej sesji — przy pracy równoległej w katalogu worktree lane'a).
Orkestrator poprowadzi plan, jego recenzję i implementację sam i wróci do właściciela
przy eskalacji oraz z raportem końcowego review. Etapy można też uruchamiać pojedynczo
(`/pipeline:plan NNN` itd.).
