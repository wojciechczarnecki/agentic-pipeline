# CHANGELOG

Wersjonowanie semantyczne. Wydanie znaczone tagiem przez `claude plugin tag`.

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
