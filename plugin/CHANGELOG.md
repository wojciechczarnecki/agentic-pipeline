# CHANGELOG

Wersjonowanie semantyczne. Wydanie znaczone tagiem przez `claude plugin tag`.

## 0.3.4

Strażnik domyka znane przecieki przy pushu i aliasach gita; dokumentacja strażnika
(`docs/GUARD.md`) i README pluginu po angielsku.

**wpływ na konsumenta:** brak kroków migracji. Nowe odmowy strażnika: push, którego
refspec zbudowano ze zmiennych albo z podstawienia komendy, a strażnik nie umie go
rozwinąć — np. `git push origin HEAD:$(git branch --show-current)`,
`git push $(git remote) <gałąź>`, `git push origin $NIEZNANA`; prefiksowe przypisanie
dla refspecu tego samego pusha (`B=feat/x git push origin $B`); `git -c alias.*`;
zapis aliasu w konfiguracji gita, także `--unset` i `--rename-section … alias`;
usunięcie albo przemianowanie sekcji `core`; `git push --all`/`--branches`, refspec ze
wzorcem albo rozwinięciem nawiasów (`*`, `?`, `{a,b}`); zapis albo `-c` konfiguracji
pusha (`remote.<nazwa>.push`, `remote.<nazwa>.mirror`, `push.default`);
`git config --edit`; klucz konfiguracji gita zbudowany ze zmiennej; push ze zmienną
przypisaną w bloku `if`/`while`/`for`/`case`, przez `read`/`declare`/`printf -v`/`unset`
albo przez `B+=`. Branch trzeba w takim pushu wypisać wprost.

### Naprawione

- Refspec pusha zbudowany ze zmiennych jest rozwijany tak jak ścieżka dla `rm`: zmienne
  z sesji, wcześniejszych przypisań i `export`; wynik wskazujący `main`/`master` jest
  blokowany z uzasadnieniem o pushu na `main` (także `${B}`, `HEAD:$B`, `"$B"`,
  `refs/heads/$B`). Wcześniej `B=main; git push origin $B` przechodził.
- Refspec, którego nie da się rozwinąć (nieznana zmienna, `$(...)`, backticki,
  przypisanie warunkowe za `||`/`&&`), jest blokowany, a uzasadnienie podaje refspec
  i prosi o wpisanie gałęzi wprost. Podstawienie komendy w miejscu remote'a też.
- Semantyka powłoki: prefiksowe przypisanie nie rozwija argumentów tej samej komendy,
  pusta wartość znika (`E=; git push origin $E` pushuje bieżącą gałąź — na `main`
  blokowane), a wartość ze spacjami dzieli się na słowa (`B="feat/x main"`).
- Zmienna w miejscu remote'a z dosłownymi refspecami przechodzi
  (`git push $REMOTE feat/x`); `git push $REMOTE main` dalej jest blokowany.
- Odczyt `core.hooksPath` bez wartości (`git config core.hooksPath`, z `--global`,
  `--local`, `--show-origin`, `--file`) przechodzi; zapis, `--unset`, `set`/`unset`
  i `-c core.hooksPath=…` dalej są blokowane. Jeden parser odróżnia odczyt od zapisu
  w formie klasycznej i w podkomendach gita 2.46.
- Alias gita jest blokowany: `git -c alias.*=…` (klucz bez rozróżniania wielkości liter)
  i zapis aliasu w konfiguracji w dowolnym zakresie; odczyt aliasu przechodzi. Inne
  klucze `-c` (np. `user.name`) bez zmian.
- Po końcowym review: strażnik śledzi zmienną tylko tam, gdzie jej wartość jest pewna.
  Przypisanie w podpowłoce `( … )`, w potoku i w tle kończy się razem z nimi (tak samo
  `cd`); `bash -c` widzi tylko zmienne eksportowane (`export -n` odbiera eksport);
  przypisanie warunkowe (także warunkowy `export`), w bloku `if`/`while`/`for`/`case`,
  przez wbudowane polecenia (`read`, `declare`, `local`, `unset`, `printf -v`, `mapfile`
  …), dopisanie `B+=`, element i tablica dają wartość nieznaną; po zmianie `IFS` każde
  rozwinięcie w refspecu jest nieznane. Wcześniej m.in. `(B=feat/x); git push origin $B`
  i `B=feat/x; bash -c 'git push origin $B'` przechodziły na `main`.
- Komenda za słowem kluczowym `if`, `while`, `until`, `elif` i `!` jest sprawdzana —
  wcześniej `if git push origin main; then :; fi` przechodził.
- Opcje pusha są czytane po rozwinięciu zmiennych: `B=-f; git push origin $B`,
  `--delete`, `--mirror` i `--no-verify` ze zmiennej są blokowane. Wartość opcji `-o`/
  `--push-option`/`--repo`/`--receive-pack`/`--exec` nie jest brana za remote (wcześniej
  `git push -o ci.skip origin` na `main` przechodził); z `--repo` każdy argument jest
  refspecem.
- Push, który sięga `main` bez wypisania go, jest blokowany: `--all`, `--branches`,
  wzorce i nawiasy w refspecu, skrót `heads/main` (git dopełnia go do
  `refs/heads/main`), konfiguracja pusha przez `-c` i zapis `remote.*.push`,
  `remote.*.mirror`, `push.default` oraz operacje na sekcjach `push` i `remote.*`.
- `git config --edit`/`-e`/`edit` jest blokowany (edytor może zmienić `core.hooksPath`
  albo alias), tak samo klucz `git config` i `git -c` zbudowany ze zmiennej, której
  strażnik nie zna; znana zmienna jest rozwijana przed sprawdzeniem klucza.

### Dodane

- `docs/GUARD.md` (po angielsku): model zagrożeń, trzy warstwy (strażnik → `pre-push` →
  rulesety GitHuba), tabela komend, które omijają regułę `deny` opartą na napisie, a
  strażnik je zatrzymuje — zmierzona `claude -p --settings` i sprawdzana testem przez
  strażnika — fail-open i znane ograniczenia.

### Zmienione

- `README.md` pluginu po angielsku; sekcja strażnika to streszczenie z linkiem do
  `docs/GUARD.md`. Skille i agenci zostają po polsku do etapu 8.

## 0.3.3

Poprawki po pierwszym pełnym przebiegu 0.3.2 u konsumenta.

**wpływ na konsumenta:** brak kroków migracji; `gh api -X DELETE` poza terenem
właściciela przestaje być blokowane.

### Naprawione

- Strażnik blokował każde `gh api -X DELETE` z komunikatem o merge'ach i ochronie
  gałęzi — także usuwanie artefaktów Actions. Teraz DELETE jest blokowane tylko na
  ścieżkach, które są decyzją właściciela: samo repozytorium i organizacja (także pod
  prefiksem, np. `api/v3` GitHub Enterprise Server, i jako `repositories/<id>`), refy
  gałęzi i tagów, merges, protection, rulesets, releases, przebiegi workflow, secrets,
  variables, environments, hooks, klucze, dostęp współpracowników, zespoły i członkowie
  organizacji, Pages, deployments i ustawienia bezpieczeństwa; komunikat podaje ścieżkę
  i regułę, która zadziałała. Ścieżka zbudowana ze zmiennych jest blokowana — nie da się
  jej sprawdzić.
- `final-review` (tryb `apply`) brał link do przebiegu z `gh run list --workflow CI` —
  nazwa workflow z projektu źródłowego, u konsumenta nieistniejąca. Link pochodzi teraz
  z `gh pr checks <nr> --json name,workflow,link`.
- Kontrakt agenta etapu mówi, że licznik `escalations` zwiększa wyłącznie orkiestrator —
  w przebiegu konsumenta podbił go reviewer w trybie `apply`.

### Zmienione

- Odmowa strażnika dla polecenia złożonego wskazuje zablokowane części i mówi, ile
  pozostałych przeszło, żeby agent mógł je puścić osobnym wywołaniem. Potok (`|`) to
  jedna część.
- `ship`: zamiast „agent etapu działa na pierwszym planie" — czekasz na jego wynik, zanim
  pójdziesz dalej (harness uruchamia agentów w tle; liczy się oczekiwanie, nie tryb).

## 0.3.2

Projekt przestaje włączać plugin. Sesja startująca w katalogu, którego
`.claude/settings.json` ma `"enabledPlugins": {"pipeline@<marketplace>": true}`, sama
zakłada instalację `--scope project` — także obok istniejącej instalacji `--scope user` —
a `claude plugin update --scope user` podnosi tylko wpis `user`, więc duplikat `project`
zostaje na starej wersji na zawsze (zmierzone 2026-09-21 na izolowanym
`CLAUDE_CONFIG_DIR` z lokalnym marketplace'em). Z samym `extraKnownMarketplaces` wpis
`project` nie powstaje, a plugin z instalacji `user` ładuje się normalnie.

**wpływ na konsumenta:** usuń `enabledPlugins` z własnego `.claude/settings.json`
(zostaw `extraKnownMarketplaces`; opt-out z wartością `false` zostaje) i zacommituj,
potem w katalogu każdego repozytorium z pluginem odinstaluj duplikat: `claude plugin
uninstall pipeline@<nazwa> --scope project` i `git checkout -- .claude/settings.json`
(komenda potrafi wyciąć blok marketplace'u). `claude plugin list` ma pokazać plugin raz,
w zakresie `user`.

### Naprawione

- `templates/settings.json` nie ma `enabledPlugins`; `/pipeline:init` go nie wpisuje.

### Zmienione

- README, Instalacja: przykład deklaruje tylko `extraKnownMarketplaces`, wyjaśnia, dlaczego
  projekt nie deklaruje `enabledPlugins: true`, i jak usunąć istniejący duplikat
  `project`; migracja z rejestracji na tagu nie przywraca `enabledPlugins`, a weryfikacja
  sprawdza brak wpisu `project`. Instalacja `--scope project` nie jest już opcją dla
  izolacji wersji — jedyna instalacja to `user`.

## 0.3.1

Naprawa wywołania kontroli metryk z 0.3.0. Skille etapów uruchamiały
`python3 "${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py" --check`, a szablon zezwalał na to
regułą zapisaną z tą samą zmienną. W treści skilla zmienna jest podstawiana, w regułach
`permissions` — nie, więc reguła nigdy nie pasowała, każdy `--check` kończył się pytaniem
o zgodę, na które subagent etapu nie odpowie, a `final-review` w trybie `apply` nie mógł
ustawić `done`.

**wpływ na konsumenta:** w `permissions.allow` własnego `.claude/settings.json` zamień wpis
na `"Bash(workflow_metrics.py *)"` (zmiana szablonu dotyczy tylko nowych projektów).
W `extraKnownMarketplaces` ustaw `"ref": "stable"` zamiast tagu wydania i raz na maszynę
przejdź na kanał `stable` z instalacją `--scope user`: `claude plugin marketplace remove
<nazwa>`, `claude plugin marketplace add '<url>#stable'`, `claude plugin install
pipeline@<nazwa> --scope user`, a potem `git checkout -- .claude/settings.json` w każdym
repozytorium z pluginem (te komendy kasują blok pluginu z `settings.json`). Kolejne
wydania: `claude plugin marketplace update <nazwa> && claude plugin update
pipeline@<nazwa> --scope user`, bez `remove`.

### Naprawione

- Kroki zamykające `plan`, `plan-review`, `implement` i `final-review` (także zamknięcie
  w trybie `apply`) wywołują `workflow_metrics.py --check <spec-dir>` przez `PATH` —
  Claude Code dopisuje `bin/` pluginu do `PATH` sesji.
- `templates/settings.json` zezwala na `Bash(workflow_metrics.py *)`.
- `templates/docs/CONVENTIONS.md` podaje wywołanie przez `PATH` zamiast
  `python3 <plugin>/bin/workflow_metrics.py`.

### Zmienione

- README: raport i `--check` w formie `PATH`, z wyjaśnieniem, dlaczego nie
  `${CLAUDE_PLUGIN_ROOT}`.
- Kanał wydań `stable` zamiast pinu na tag: `templates/settings.json` ma `"ref": "stable"`
  (zamiast `TODO:` z tagiem), a `/pipeline:init` wpisuje `stable` zamiast wyprowadzać tag
  z wersji w `${CLAUDE_PLUGIN_ROOT}`. `ref` marketplace'u jest globalny na maszynę, więc
  pin na tag wymuszał przy każdym wydaniu `remove`, które odinstalowuje plugin we
  wszystkich projektach.
- README, Instalacja: domyślnie `--scope user` (jedna instalacja na maszynę; `--scope
  project` jako opcja dla izolacji), aktualizacja przez `marketplace update` + `plugin
  update`, jednorazowa migracja z rejestracji na tagu (z ostrzeżeniem, że `remove`
  odinstalowuje plugin we wszystkich projektach, a `remove`, `add` i `install` kasują
  blok pluginu z `.claude/settings.json`) i wyłączenie pluginu w repozytorium przez
  `"enabledPlugins": {"pipeline@<marketplace>": false}`.

## 0.3.0

Reguły trafiają tam, gdzie agent je wykonuje, i dostają program, który ich pilnuje.
Format bloku `metrics:` jest nazwany w każdym skillu etapu i sprawdzany przez
`workflow_metrics.py --check`, kontrakt agenta etapu żyje w plikach `agents/*.md`
(harness wczytuje je bez odczytu narzędziem), a instrukcja instalacji pinuje wydanie.

**wpływ na konsumenta:** po aktualizacji zarejestruj marketplace ponownie z nowym `ref`
(`claude plugin marketplace remove <nazwa>` + `add '<url>#pipeline--v0.3.0'`) — bez tego pin
w `.claude/settings.json` jest bezczynny; dopisz do `permissions.allow` we własnym
`.claude/settings.json` wpis
`"Bash(python3 \"${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py\" *)"` (zmiana szablonu
dotyczy tylko nowych projektów); spec zaczęty przed tym wydaniem może raz eskalować
brakującymi kluczami metryk — uzupełnia je właściciel, agent ich nie zmyśla.

### Dodane

- `bin/workflow_metrics.py --check <katalog-speca>` — komplet kluczy należnych dla
  osiągniętego statusu, parsowalne znaczniki czasu i zgodność
  `findings_accepted + findings_rejected` z sumą znalezisk końcowego review; kod 1
  i czytelny komunikat nazywający każdy brak. `--check` zgłasza też klucz spoza listy
  metryk (literówka gubiłaby wartość po cichu) i osobno nazywa frontmatter bez `status`.
  Domyślne wywołanie (raport) bez zmian poza tym, że nieistniejący katalog speców kończy
  się kodem 1 z komunikatem zamiast „brak metryk", a niedostępnego `SPEC.md` raport
  pomija z ostrzeżeniem zamiast tracebacku.
- Testy strukturalne `test_stage_skills.py` i `test_stage_contract.py`.
- Skill `init` sprawdza obecność `AskUserQuestion` PRZED krokiem z pytaniami i bez tego
  narzędzia nie pyta żadną drogą — także nie prozą — ani nie kończy odpowiedzi prośbą
  o decyzję. Wcześniej reguła stała dopiero za krokiem „zadaj pytania", więc bywała
  ważona zamiast wykonywana: dwa przebiegi ewaluacyjne tego samego commita rozjechały
  się, jeden dokończył skill, drugi zadał cztery pytania tekstem i stanął.

### Zmienione

- Każdy skill etapu nazywa w kroku zamykającym format bloku `metrics:` i własne klucze
  oraz uruchamia `--check` przed zgłoszeniem sukcesu; `final-review` w trybie `apply` nie
  ustawia `done`, dopóki `--check` kończy się błędem. Żaden skill nie odsyła po format
  metryk do README.
- „Kontrakt agenta etapu" i „Wyzwalacze eskalacji" są w całości w `agents/*.md`; agenci nie
  każą już czytać skilla `ship` (test pilnuje zgodności co do znaku).
- Sekcja „Konfiguracja projektu" w sześciu skillach etapów to dwa punkty; tabela kluczy
  została tylko w README. Reguła artefaktów wizualnych to jedno zdanie rozkazujące,
  warunkowe na zakresie UI w `verify.scopes`, z odesłaniem do konwencji projektu.
- `templates/settings.json` wskazuje źródło `git` po HTTPS z widocznym `ref` (TODO)
  i pozwala na jedno konkretne wywołanie
  `Bash(python3 "${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py" *)` — wzorzec jest
  zakotwiczony na całym literale, więc nie przepuszcza dowolnej komendy `python3`;
  `init` podstawia nazwę marketplace'u i `ref` ze ścieżki `${CLAUDE_PLUGIN_ROOT}`,
  a przy innym kształcie zostawia `TODO:`.
- `final-review` w trybie `apply`: znalezisko odłożone do backlogu liczy się jako
  `findings_rejected`, żeby bilans `--check` się zgadzał.
- README: sekcja o `--check` (kody wyjścia, tabela kluczy należnych według statusu)
  i wywołanie przez `${CLAUDE_PLUGIN_ROOT}` zamiast ścieżki względnej; `ref` w przykładzie
  deklaratywnym, zastrzeżenie o ponownej rejestracji
  marketplace'u i jednozdaniowy zakres modułu migracji (tylko Alembic).

## 0.2.0

Pierwsze wydanie w tym repozytorium — zaimportowane z prywatnego repozytorium projektu
bez zmiany zachowania skilli, agentów, hooków ani strażnika.

Skille etapów prowadzą do dokumentów domenowych przez mapę dokumentów w `CLAUDE.md`
projektu, a SPEC pokazuje, co agent przeczytał. Nowa sekcja SPEC zmienia wyjście etapu
`idea`, dlatego wydanie minor.

### Zmienione

- `idea`, `plan` i `implement` odsyłają do dokumentów domenowych z mapy dokumentów
  w `CLAUDE.md` (według warunków w mapie) zamiast listy w dokumencie stylu kodu.
- Krok 1 `idea`: gotowy zakres lub wymagania w prompcie nie zwalniają ze zbierania
  kontekstu.
- Szablon SPEC ma sekcję „Przeczytany kontekst" — jedna pozycja na roadmapę, opis
  projektu, rejestr decyzji i każdy dokument domenowy; guardrail wymaga jej dla
  `spec-ready`.

## 0.1.0

Pierwsza wersja — wydzielenie workflow agentowego do samodzielnego pluginu.

### Dodane

- Siedem skilli: `init`, `idea`, `plan`, `plan-review`, `implement`, `final-review`, `ship`.
- Czterech agentów etapów: `planner`, `plan-reviewer`, `implementer`, `reviewer`.
- Strażnik komend (`bin/guard`, `bin/guard.py`) z regułami uniwersalnymi działającymi bez
  konfiguracji oraz modułami produkcji, worktree i migracji sterowanymi konfiguracją.
- Hooki `PostToolUse` (formatowanie według mapy `format[]`) i `PreToolUse:
  AskUserQuestion` / `Notification` (powiadomienie o oczekiwaniu na właściciela).
- Warstwa konfiguracji `.claude/workflow.json` (`bin/workflow_config.py`) z walidacją
  kluczy i dokumentowanymi wartościami domyślnymi.
- Zestawienie metryk workflow (`bin/workflow_metrics.py`).
- Szablony projektu: `settings.json`, `workflow.example.json`, `CLAUDE.md`, dokumenty
  `docs/`, hook `pre-push` oraz warianty CI (Python, Node, szkielet), audytu
  bezpieczeństwa i `dependabot.yml`.
