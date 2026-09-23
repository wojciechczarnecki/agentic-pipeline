---
name: init
description: Stawia w repozytorium szkielet pod pipeline — .claude/workflow.json, uprawnienia, CLAUDE.md, dokumenty projektu, hook pre-push i szablony CI. Użyj w nowym repozytorium albo gdy strażnik zgłasza brak .claude/workflow.json.
argument-hint: <opcjonalnie: nazwa projektu i problem, który rozwiązuje>
---

# /pipeline:init — szkielet projektu pod pipeline

Rola: instalator, nie architekt. Stawiasz minimum, na którym pipeline działa: konfigurację,
dokumenty do wypełnienia, uprawnienia, hook gita i CI. Pełna wizja i wymagania należą do
`/pipeline:idea` przy pierwszym feature — nie rób z inicjalizacji wywiadu projektowego.

## Wejście / wyjście

- Wejście: repozytorium (także puste, zaraz po `git init`).
- Wyjście: pliki z listy niżej + wypisana instrukcja włączenia hooka gita.

## Zakres zapisu (bezwzględny)

Zapisujesz WYŁĄCZNIE w: `.claude/`, `CLAUDE.md`, `docs/`, `scripts/`, `.github/`.
Nic poza tymi prefiksami — żadnych plików źródłowych, konfiguracji narzędzi ani
`.gitignore`. Nie commitujesz; commit należy do właściciela.

## Kroki

1. **Rozpoznaj teren.** Sprawdź, czy katalog jest repozytorium gita (`git rev-parse
   --is-inside-work-tree`) i które z plików z listy już istnieją. Autowykryj stack:
   `pyproject.toml` → Python, `package.json` → Node, oba → oba, żaden → nieznany.
   Zajrzyj do wykrytych plików po nazwy skryptów (`scripts` w `package.json`, narzędzia
   lintu i testów w `pyproject.toml`) — to wypełni `verify` i `format` bez pytania.
2. **Sprawdź, czy masz `AskUserQuestion`. Jeśli go nie ma — pomiń ten krok i przejdź do
   kroku 3.** Nie zadajesz wtedy pytań ŻADNĄ drogą: ani narzędziem, ani zwykłym tekstem,
   i nie czekasz na odpowiedź, bo nie ma jej od kogo dostać.
   Mając `AskUserQuestion` — **zadaj pytania: jedna runda, maksymalnie 4** (każde pytanie
   z rekomendacją: opcja pierwsza z dopiskiem „(Recommended)" w etykiecie):
   1. język plików projektu (`language`): `en` „(Recommended)" albo `pl` — rekomendujesz
      `en`, bo to wartość domyślna i język, którego oczekują czytelnicy spoza projektu;
      gdy `.claude/workflow.json` ma już obsługiwany `language` (`en` albo `pl`),
      rekomendujesz tę istniejącą wartość — przyjęcie rekomendacji nie zmienia języka
      projektu; odpowiedź decyduje o dokumentach, specach, planach i treści PR;
   2. nazwa projektu i problem, który rozwiązuje (jedno zdanie);
   3. potwierdzenie wykrytego stacku i komendy pełnej weryfikacji;
   4. produkcja poza zasięgiem agenta — hosty i komendy CLI (albo „brak produkcji").
   Pytania zadajesz w języku sesji Claude Code — odpowiedź o `language` rządzi plikami,
   nie rozmową.
   **Druga runda tylko wtedy, gdy autowykrycie stacku zawiodło** — pytasz wówczas
   o komendę weryfikacji, komendy formatowania i katalog hooków gita. W żadnym innym
   przypadku drugiej rundy nie ma.
3. **Tryb nieinteraktywny** (`claude -p`, brak `AskUserQuestion`): NIE pytasz i NIE
   blokujesz. Pytanie zadane prozą i zakończenie odpowiedzi prośbą o decyzję to też
   blokada — kończysz zadanie do końca na wartościach, które masz, a nie pytaniem.
   Pliki w `.claude/` Claude Code traktuje jako wrażliwe i pyta o zgodę na ich zapis
   niezależnie od reguł uprawnień, więc komplet plików powstaje tylko w sesji
   uruchomionej z `--permission-mode bypassPermissions`; przy słabszym trybie zapisujesz
   wszystko poza `.claude/`, a pominięte pliki wypisujesz z treścią do wklejenia i kończysz
   sukcesem. Brakujące wartości zapisujesz jako `TODO:` — w `.claude/workflow.json`
   (np. `"command": "TODO: <verify command>"`, z opisem po `TODO:` w języku z `language`)
   i w nagłówkach dokumentów.
   Wyjątek — `language`: bierzesz go z argumentu, gdy argument wskazuje język (`en`,
   `pl` albo jego nazwa: English/angielski, polski/po polsku); bez takiego argumentu
   zostawiasz obsługiwany `language` z istniejącego `.claude/workflow.json`, a gdy go
   nie ma — ustawiasz `en`; nigdy ze znacznikiem `TODO:`, bo `en` to wartość domyślna.
   Język, w którym napisano prompt, nie jest takim wskazaniem.
   Kończysz sukcesem, wypisując listę wartości do uzupełnienia.
4. **Wygeneruj pliki** z `${CLAUDE_PLUGIN_ROOT}/templates/`, podstawiając odpowiedzi.
   **Szablony przenoś powłoką** (`cp`, `cat`, `sed`), nie narzędziami Read/Glob: katalog
   pluginu leży poza katalogiem roboczym sesji, więc odczyt narzędziem bywa tam blokowany
   albo czeka na zgodę, której w trybie nieinteraktywnym nie ma. Najpierw skopiuj plik do
   projektu, dopiero potem edytuj go narzędziem Edit. Gdyby także powłoka nie sięgnęła
   katalogu pluginu — przerwij bez zapisu i poproś o `--add-dir
   ${CLAUDE_PLUGIN_ROOT}`; NIE odtwarzaj szablonów z pamięci.
   **Wyjątek — pliki w `.claude/`:** ich zapisu z powłoki strażnik nie przepuszcza (to
   pliki strażnicze). Treść szablonu WCZYTAJ powłoką (`cat`), a docelowy plik zapisz
   narzędziem Write — to jedyna sankcjonowana droga. Blokada z powłoki nie jest powodem
   do rezygnacji z pliku.
   Lista plików:
   - `.claude/settings.json` — z `templates/settings.json` (permissions allow/ask/deny,
     `extraKnownMarketplaces`). **Bez sekcji `hooks`** — hooki
     dostarcza plugin; zdublowanie ich tutaj uruchomiłoby strażnika dwa razy.
     **Bez `enabledPlugins`** — sesja w katalogu, który włącza plugin w
     `.claude/settings.json`, sama zakłada instalację `--scope project` obok instalacji
     `user`, a `claude plugin update --scope user` jej nie podnosi.
     Podstaw dwie rzeczy: w regule `ask` ścieżkę katalogu hooków gita na `gitHooksDir`
     tego projektu (reguła z inną ścieżką chroni pustkę) oraz źródło marketplace'u.
     Nazwę marketplace'u odczytaj ze ścieżki `${CLAUDE_PLUGIN_ROOT}`
     (`…/<marketplace>/<plugin>/<wersja>/`): idzie w klucz `extraKnownMarketplaces`.
     `ref` to zawsze `"stable"` — kanał wydań, gałąź przesuwana
     na każdy nowy tag; nie wyprowadzaj go z wersji w ścieżce, bo pin na tag wymusza
     ponowną rejestrację marketplace'u przy każdym wydaniu. `url` weź z listy
     marketplace'ów sesji. Gdy ścieżka ma inny kształt albo url jest nieznany — zostaw
     `TODO:` przy tej wartości i wymień ją na liście do uzupełnienia z kroku 7.
     To jedyny generowany plik, którego zapis wymaga zgody właściciela; gdy sesja
     nieinteraktywna go nie dostanie, wypisz plik na liście do dopisania ręcznie
     (wraz z jego treścią) i kończ sukcesem — reszta szkieletu i tak stoi;
   - `.claude/workflow.json` — z `templates/workflow.example.json`, przycięty do tego
     projektu: sekcja `migrations` zostaje tylko wtedy, gdy projekt ma narzędzie migracji;
     `production`, `verify`, `format`, `docs`, `gitHooksDir` wypełnione odpowiedziami
     albo `TODO:`; `language` to zawsze `en` albo `pl` (odpowiedź, argument, istniejąca
     wartość albo `en`), nigdy `TODO:`; klucza `protectedBranches` nie zapisujesz (kanał wydań
     chroni właściciel ręcznie, po `/pipeline:init`);
   - `CLAUDE.md` — z `templates/CLAUDE.<language>.md` (szablon w języku z `language`),
     z mapą dokumentów przepisaną na ścieżki z `docs.*` (inaczej instrukcja dla agentów
     wskazuje inne pliki niż konfiguracja);
   - `docs/PROJECT.md`, `docs/ROADMAP.md`, `docs/BACKLOG.md`, `docs/DECISIONS.md`,
     `docs/CONVENTIONS.md` — każdy z `templates/docs/<NAZWA>.<language>.md`, zapisany pod
     nazwą docelową bez przyrostka języka;
   - `scripts/git-hooks/pre-push` — z `templates/pre-push`, **z bitem wykonywalności**
     (`chmod +x`); ścieżka katalogu zgodna z `gitHooksDir`;
   - `.github/workflows/ci.yml` — złożony z wariantów według wykrytego stacku:
     Python → job z `templates/github/workflows/ci-python.yml`, Node → job
     z `ci-node.yml`, oba → OBA joby w jednym pliku, żaden → `ci-placeholder.yml`;
   - `.github/workflows/security.yml` — tak samo z `security-python.yml` /
     `security-node.yml`; przy nieznanym stacku plik z jednym jobem do uzupełnienia;
   - `.github/dependabot.yml` — z `templates/github/dependabot.yml`, z wpisami
     ekosystemów wykrytego stacku; wpis `github-actions` zostaje ZAWSZE, niezależnie
     od stacku.
5. **Istniejące pliki.**
   - tryb interaktywny: pokaż różnicę (co dopisujesz / zmieniasz) i ZAPYTAJ przed
     nadpisaniem — osobno dla każdego pliku;
   - tryb nieinteraktywny: istniejącego pliku NIGDY nie nadpisujesz — pomijasz go
     i wypisujesz na liście pominiętych.
6. **Idempotencja.** Drugie uruchomienie nie odtwarza szablonu na siłę: treść dopisana
   przez użytkownika (nowa sekcja w `CLAUDE.md`, wiersz w rejestrze decyzji, pozycja
   w backlogu) zostaje nietknięta. Zmieniasz wyłącznie to, co wynika z NOWYCH odpowiedzi;
   plików, których nowe odpowiedzi nie dotyczą, nie zapisujesz wcale — `git status`
   ma po takim przebiegu milczeć na ich temat. Odpowiedź o języku inna niż istniejący
   `language` zmienia wyłącznie `language` w `.claude/workflow.json`: istniejących
   dokumentów nie tłumaczysz ani nie podmieniasz na szablon w nowym języku (w nowym
   powstaje tylko plik, którego brakowało), a w zamknięciu mówisz właścicielowi, że
   zostają w dotychczasowym języku.
7. **Zamknięcie.** Wypisz właścicielowi:
   - listę utworzonych, zaktualizowanych i pominiętych plików;
   - wartości `TODO:` do uzupełnienia;
   - przy zmianie `language` — że istniejące dokumenty zostały w dotychczasowym języku;
   - instrukcję włączenia hooka gita: `git config core.hooksPath <gitHooksDir>`
     (raz na klon — inaczej `pre-push` nie działa);
   - następny krok: `/pipeline:idea` dla pierwszego feature'a.

## Guardraile

- Nie zgaduj wartości, których nie potwierdził właściciel ani kod — od tego jest `TODO:`.
- Nie dopisuj do `.claude/settings.json` sekcji `hooks` ani wpisów uprawnień specyficznych
  dla narzędzi, których w repozytorium nie widać.
- Nie twórz katalogu speców z przykładowym specem — pierwszy spec tworzy
  `/pipeline:idea`.
- Nie uruchamiaj `git config core.hooksPath` sam — to zmiana konfiguracji klona,
  którą wykonuje właściciel (i którą blokuje strażnik).
- Nie commitujesz i nie pushujesz.
