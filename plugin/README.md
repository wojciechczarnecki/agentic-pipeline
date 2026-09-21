# Plugin `pipeline`

Agentowy pipeline feature'a dla Claude Code: pomysł → plan → recenzja planu → implementacja
→ końcowe review → PR. Do tego strażnik komend (`main`, produkcja, migracje, kasowanie
plików), hooki formatowania i powiadomień, zestawienie metryk workflow oraz skill stawiający
szkielet nowego projektu.

Plugin jest niezależny od stacku i od domeny: wszystko, co dotyczy konkretnego repozytorium,
żyje w jego `.claude/workflow.json`.

## Instalacja

**Ze ścieżki lokalnej** (podgląd, praca nad samym pluginem):

```bash
claude --plugin-dir ./plugin          # jednorazowa sesja z pluginem
claude plugin validate --strict ./plugin
```

**Przez marketplace — katalog lokalny:**

```bash
claude plugin marketplace add /ścieżka/do/klonu-agentic-pipeline
/plugin install pipeline@wcz-tools
```

**Przez marketplace — repozytorium na GitHubie** (publiczne, HTTPS, bez klucza SSH),
kanał wydań `stable`:

```bash
claude plugin marketplace add 'https://github.com/wojciechczarnecki/agentic-pipeline.git#stable'
claude plugin install pipeline@wcz-tools --scope user
```

`stable` to gałąź, którą właściciel przesuwa na każdy nowy tag wydania
(`pipeline--vX.Y.Z`). Bez `ref` konsument śledzi `main`, czyli kod niewydany. `ref`
marketplace'u jest globalny na maszynę (`~/.claude/plugins/known_marketplaces.json`),
a `install` i `update` nie przyjmują wersji — dlatego kanał, a nie pin na tag: pin
wymuszałby przy każdym wydaniu `marketplace remove` i ponowną instalację w każdym
projekcie.

**Zakres `user` — jedna instalacja na maszynę.** Plugin działa w każdym katalogu, bez
instalowania go osobno w każdym repozytorium i każdym klonie. Instalacja
`--scope project` jest przypisana do katalogu (wpis z `projectPath` w
`~/.claude/plugins/installed_plugins.json`; w innym repozytorium `claude plugin list`
pokaże plugin jako `enabled`, a komend `/pipeline:*` nie będzie) i nie podnosi jej
`claude plugin update --scope user` — nie używaj jej; jedyna instalacja to `user`.

W `.claude/settings.json` projektu (kształt jak w `templates/settings.json`) deklaruj
tylko źródło — tak świeży klon na innej maszynie dowie się, skąd pochodzi plugin:

```json
{
  "extraKnownMarketplaces": {
    "wcz-tools": {
      "source": {
        "source": "git",
        "url": "https://github.com/wojciechczarnecki/agentic-pipeline.git",
        "ref": "stable"
      }
    }
  }
}
```

**Projekt NIE deklaruje `"enabledPlugins": {"pipeline@<nazwa>": true}`.** Sesja
startująca w katalogu, który tak włącza plugin, sama zakłada instalację `--scope
project` — także obok istniejącej instalacji `user` — a `claude plugin update
--scope user` podnosi tylko wpis `user`, więc duplikat `project` zostaje na starej wersji
na zawsze (zmierzone 2026-09-21: `claude plugin list` pokazuje plugin dwa razy; bez
`enabledPlugins`, z samym `extraKnownMarketplaces`, wpis `project` nie powstaje, a plugin
z instalacji `user` ładuje się normalnie). Istniejący duplikat usuń tak: najpierw
zacommituj `.claude/settings.json` bez `enabledPlugins` (inaczej `git checkout` przywróci
deklarację, a następna sesja założy duplikat od nowa), potem w katalogu repozytorium:

```bash
claude plugin uninstall pipeline@<nazwa> --scope project
git checkout -- .claude/settings.json   # komenda potrafi wyciąć blok marketplace'u
```

**Aktualizacja** do nowego wydania, bez ponownej rejestracji:

```bash
claude plugin marketplace update wcz-tools && claude plugin update pipeline@wcz-tools --scope user
```

Potem nowa sesja — działająca trzyma to, co wczytała przy starcie.

**Jednorazowa migracja z rejestracji na tagu** (marketplace dodany wcześniej jako
`'<url>#pipeline--vX.Y.Z'` albo bez `ref`). Sprawdź wpis marketplace'u w
`~/.claude/plugins/known_marketplaces.json`: jego `source.ref` ma brzmieć `"stable"`.
Jeśli nie:

```bash
claude plugin marketplace remove <nazwa>
claude plugin marketplace add '<url>#stable'
claude plugin install pipeline@<nazwa> --scope user
git checkout -- .claude/settings.json   # w KAŻDYM repozytorium z pluginem
```

**`remove` odinstalowuje plugin we WSZYSTKICH projektach** — marketplace jest źródłem
instalacji. **Wszystkie trzy komendy (`remove`, `add`, `install`) kasują
`extraKnownMarketplaces` z `.claude/settings.json`** (projektu i
`~/.claude/settings.json`) i żadna go nie przywraca — stąd `git checkout` w każdym
repozytorium, które ma ten blok (bez `enabledPlugins`, patrz wyżej). Oba skutki są
ciche: sesja bez pluginu nie ma strażnika komend i nic nie zgłasza. Po migracji uruchom
nową sesję.

**Weryfikacja** po instalacji, aktualizacji albo migracji, w nowej sesji: `claude plugin
list` pokazuje plugin w wydanej wersji w zakresie `user` — i tylko tam, bez wpisu
`project` — a komenda, którą strażnik
blokuje — np. `sed -i` na `.claude/settings.json` — jest faktycznie odrzucana, z wersją
w ścieżce, którą zgłasza. Dopiero drugi test dowodzi, że plugin jest wczytany w tym
repozytorium; pierwszy dowodzi tylko, że instalacja jest poprawna.

**Wyłączenie w repozytorium, które pluginu nie chce.** Przy instalacji `user` plugin —
w tym strażnik komend — działa wszędzie, także tam, gdzie commituje się prosto na `main`
i strażnik by to blokował. Wyłącz go w `.claude/settings.json` takiego repozytorium:

```json
{ "enabledPlugins": { "pipeline@wcz-tools": false } }
```

To jedyne uprawnione użycie `enabledPlugins` w projekcie — tylko z wartością `false`.

W każdym projekcie uruchom raz `/pipeline:init`, żeby powstał `.claude/workflow.json`
i reszta szkieletu. W sesji nieinteraktywnej (`claude -p`) potrzebny jest
`--permission-mode bypassPermissions`: pliki w `.claude/` Claude Code traktuje jako
wrażliwe i pyta o zgodę na ich zapis niezależnie od reguł uprawnień. W słabszym trybie
init zapisze wszystko poza `.claude/` i wypisze treść pominiętych plików.

## Komendy i agenci

| Komenda | Etap |
|---|---|
| `/pipeline:init` | szkielet projektu: konfiguracja, uprawnienia, dokumenty, hook gita, CI |
| `/pipeline:idea` | krytyczny review pomysłu → SPEC.md (jedyny etap w dialogu) |
| `/pipeline:plan` | SPEC → PLAN.md z krokami i komendami weryfikacyjnymi |
| `/pipeline:plan-review` | adwersaryjny review planu, poprawki w miejscu, zatwierdzenie |
| `/pipeline:implement` | realizacja planu krok po kroku w pętli samokorekty |
| `/pipeline:final-review` | końcowe review z trzech perspektyw, poprawki, PR |
| `/pipeline:ship` | orkestrator: prowadzi feature od SPEC do otwartego PR |

Agenci etapów (uruchamiani przez `/pipeline:ship`): `pipeline:planner`,
`pipeline:plan-reviewer`, `pipeline:implementer`, `pipeline:reviewer`.

## Konfiguracja projektu — `.claude/workflow.json`

Jedyne miejsce, w którym projekt opisuje sam siebie. Pliku może nie być: wtedy obowiązują
wartości domyślne, a strażnik raz na sesję wypisuje ostrzeżenie na stderr i **nigdy nie
blokuje** z tego powodu. Nieznany klucz albo zły typ kończy się czytelnym błędem walidacji
(`python3 bin/workflow_config.py --check`), też bez blokowania sesji. Walidacja idzie
sekcjami: wadliwa sekcja wraca do wartości domyślnych z ostrzeżeniem, a pozostałe dalej
konfigurują reguły — literówka w jednym kluczu nie rozbraja strażnika w całości.

| klucz | domyślnie | znaczenie |
|---|---|---|
| `production.hosts` | `[]` | fragmenty hostów/URL-i poza zasięgiem agenta (dopasowanie bez rozróżniania wielkości liter); pusta lista = reguła nieaktywna |
| `production.commands` | `[]` | programy CLI operujące produkcją — blokowane z odesłaniem do właściciela |
| `worktree.dir` | `"../worktrees"` | katalog worktree, **ścieżką względną** do korzenia repozytorium — usuwanie w nim jest dozwolone, a `git worktree add` poza nim blokowane; wartość bezwzględna albo obejmująca korzeń repozytorium jest odrzucana z ostrzeżeniem i zastąpiona domyślną |
| `verify.command` | `"bash scripts/verify.sh"` | pełna weryfikacja stacku; sygnał pętli samokorekty |
| `verify.scopes` | `[]` | dodatkowe zakresy przekazywane do tej komendy (np. `backend`, `ui`) |
| `format` | `[]` | lista `{ "match": <glob>, "command": <komenda> }` dla hooka formatowania |
| `docs.roadmap` | `"docs/ROADMAP.md"` | dokument roadmapy |
| `docs.backlog` | `"docs/BACKLOG.md"` | backlog z priorytetami i wyzwalaczami |
| `docs.decisions` | `"docs/DECISIONS.md"` | rejestr decyzji |
| `docs.conventions` | `"docs/CONVENTIONS.md"` | konwencje kodu i procesu |
| `docs.project` | `"docs/PROJECT.md"` | wizja i wymagania |
| `docs.specsDir` | `"specs"` | katalog speców |
| `migrations` | brak sekcji | `{ "command": <program>, "localHosts": [...] }`; brak sekcji = moduł migracji nieaktywny |
| `gitHooksDir` | `"scripts/git-hooks"` | katalog hooków gita (istniejący hook chroniony przed edycją z shella, wskazywany w instrukcji) |
| `language` | `"pl"` | język dokumentów generowanych i pisanych przez skille |

Pełny przykład: `templates/workflow.example.json`.

### Formatowanie (`format[]`)

Hook `PostToolUse` pyta `bin/workflow_config.py --format-for <plik>` o komendę dla właśnie
zmienionego pliku. Glob z `match` dopasowuje się do ścieżki **względem korzenia projektu**
(`*` obejmuje też ukośniki), komenda uruchamiana jest **z korzenia projektu**, a `{file}`
podstawiane jest ścieżką względną — zawsze zacytowaną dla powłoki, więc nazwa pliku ze
spacją czy średnikiem jest argumentem, nie drugą komendą; bez tego placeholdera ścieżka
trafia na koniec komendy.
Brak mapy, brak dopasowania, brak `python3` lub błąd konfiguracji = brak formatowania
i kod wyjścia 0 — hook nigdy nie blokuje edycji.

### Strażnik komend

Hook `PreToolUse: Bash` (`bin/guard`, wrapper na `bin/guard.py`). Blokuje z kodem 2
i uzasadnieniem. Reguły uniwersalne działają BEZ konfiguracji: push/commit/merge na `main`,
`--force`, `--no-verify`, `git reset --hard`, `git clean -f`, zmiana `core.hooksPath`,
`gh pr merge`, zmiany ustawień repozytorium i sekretów, `sudo`, usuwanie plików poza
repozytorium i katalogiem tymczasowym, edycja plików strażniczych z shella
(`.claude/settings*.json`, `.claude/workflow.json`, katalog pluginu, gdy leży wewnątrz
repozytorium, oraz ISTNIEJĄCE hooki w katalogu z `gitHooksDir` — utworzenie brakującego
hooka i nadanie mu bitu wykonywalności jest dozwolone, bo nie wyłącza niczego, co działa).
Z konfiguracji dochodzą: hosty i komendy
produkcji, katalog worktree i moduł migracji.

Moduł migracji rozpoznaje WYŁĄCZNIE czasowniki Alembica (`upgrade`, `downgrade`, `stamp`,
`revision`, `current`, `check`) i zmienne `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`;
konfigurowalne są tylko `migrations.command` i `migrations.localHosts`. Projekt na innym
narzędziu migracji nie jest przez strażnika chroniony — jego milczenie nie jest ochroną.

Fail-open jest zamierzony: brak `.claude/workflow.json`, błąd walidacji i brak `python3`
kończą się ostrzeżeniem na stderr i kodem 0, nigdy odmową startu.

## Mechanika pipeline'u

### Statusy speca

Źródłem prawdy jest `status:` we frontmatterze `SPEC.md` — dlatego każdy etap da się
wznowić po przerwaniu.

| Status | Kto działa | Wynik |
|---|---|---|
| `spec-draft` | właściciel + `/pipeline:idea` | `spec-ready` (bramka 1) |
| `spec-ready` | `planner` | `plan-draft` |
| `plan-draft` | `plan-reviewer` | `plan-approved` (sam, gdy brak eskalacji) |
| `plan-approved` | `implementer` | `implemented` |
| `implemented` | `reviewer` (`report`) | raport znalezisk → bramka 2 |
| `implemented` + decyzje | `reviewer` (`apply`) | PR z zielonym CI → `done` |
| `done` | właściciel | merge PR (bramka 3) |

`plan-approved` jest zgodą na wszystkie edycje w zakresie planu — dlatego recenzent planu
nie zatwierdza planu z niezaakceptowaną zależnością ani migracją.

### Kontrakt `RESULT`

Każdy agent etapu uruchomiony przez `/pipeline:ship` kończy odpowiedź blokiem:

```
RESULT: DONE | ESCALATE
STATUS: <status speca po etapie>
METRICS: <klucz=wartość; …>
ESCALATION: <tylko przy ESCALATE — problem; opcje (≤ 4); rekomendacja; dlaczego>
SUMMARY: <≤ 10 linii; dla reviewer/report — tabela znalezisk: id | waga | jedno zdanie>
```

Agent etapu nie może pytać właściciela: wszędzie, gdzie skill każe zapytać albo zrobić
STOP, kończy blokiem `RESULT: ESCALATE`. Orkestrator zamienia to na pytanie do właściciela
i zapisuje decyzję w PLAN.md → `## Decyzje właściciela`.

### Wyzwalacze eskalacji

- nowa zależność albo podbicie wersji major istniejącej,
- migracja danych,
- luka lub sprzeczność w SPEC,
- blocker z recenzji planu, którego recenzent nie umie naprawić w samym planie,
- odstępstwo od planu zmieniające zakres, architekturę albo schemat danych,
- pętla samokorekty wyczerpana (4. iteracja na tym samym błędzie),
- test wykrywa wadę produktu, której naprawa wykracza poza zakres planu lub decyzje
  właściciela — zamiast obchodzić ją zmianą testu albo danych testowych,
- konflikt przy `git merge origin/main`.

## Metryki workflow

Każdy spec niesie we frontmatterze `SPEC.md` płaski blok `metrics:`; każdy etap wpisuje
swoje klucze sam.

```yaml
metrics:
  started_at: "2026-09-15T09:00"      # /pipeline:ship lub /pipeline:plan
  plan_steps: 8                        # /pipeline:plan
  plan_review_blockers: 1              # /pipeline:plan-review — liczone przed poprawkami
  plan_review_majors: 2
  plan_changes: 5
  implement_steps: 8                   # /pipeline:implement
  implement_iterations: 3              # iteracje pętli samokorekty ponad pierwszą próbę
  deviations: 1
  escalations: 1                       # /pipeline:ship — pytania do właściciela
  final_review_blockers: 0             # /pipeline:final-review report
  final_review_worth_fixing: 3
  final_review_nits: 2
  findings_accepted: 3                 # /pipeline:final-review apply
  findings_rejected: 2
  finished_at: "2026-09-15T14:30"      # /pipeline:final-review apply (zielone CI na PR)
```

Zestawienie wszystkich speców — tabela per spec, sumy, odsetek istotnych znalezisk
złapanych przed kodem i eskalacje na spec:

```bash
workflow_metrics.py [katalog-speców]
```

Bez argumentu katalog bierze się z `docs.specsDir`. Skrypt wywołuje się po nazwie:
Claude Code dopisuje `bin/` włączonego pluginu do `PATH` sesji, także u konsumenta. Nie
przez `${CLAUDE_PLUGIN_ROOT}` — w treści skilla ta zmienna jest podstawiana, ale w regułach
`permissions` już nie, więc wywołanie ścieżką bezwzględną nie pasuje do żadnej reguły
`allow` (a w powłoce narzędzia Bash zmiennej nie ma wcale).

### Kontrola metryk (`--check`)

```bash
workflow_metrics.py --check <katalog-speca>
```

Sprawdza JEDEN spec: komplet kluczy należnych dla osiągniętego statusu, format czasów
(`%Y-%m-%dT%H:%M`), liczniki jako nieujemne liczby całkowite, brak kluczy spoza listy
metryk (literówka gubiłaby wartość po cichu) oraz bilans
`findings_accepted + findings_rejected == final_review_blockers +
final_review_worth_fixing + final_review_nits` (liczony dopiero, gdy jest wszystkie pięć).
Kod wyjścia: `0` i cisza, gdy wszystko gra; `1` z opisem KAŻDEGO problemu na stderr (nigdy
traceback); `2`, gdy argumenty są błędne. Krok zamykający każdego etapu uruchamia `--check`
przed zgłoszeniem sukcesu, a `final-review` w trybie `apply` nie ustawi `done` przy
czerwieni. Czerwieni, której etap nie naprawi z własnych artefaktów, nie wolno zasypać
wymyśloną wartością — to eskalacja do właściciela.

Klucze należne według statusu:

| status | wymagane klucze |
|---|---|
| `spec-draft`, `spec-ready` | żadne |
| `plan-draft` | `started_at`, `escalations`, `plan_steps` |
| `plan-approved` | powyższe + `plan_review_blockers`, `plan_review_majors`, `plan_changes` |
| `implemented` | powyższe + `implement_steps`, `implement_iterations`, `deviations` |
| `done` | `started_at`, `finished_at` i wszystkie liczniki z bloku wyżej |

Konsument musi mieć na liście `permissions.allow` regułę `Bash(workflow_metrics.py *)` —
subagent etapu nie odpowie na pytanie o zgodę, więc bez niej każdy `--check` staje, a
`final-review` w trybie `apply` nigdy nie ustawi `done`. `templates/settings.json` niesie ją
dla nowych projektów. Reguła zapisana z `${CLAUDE_PLUGIN_ROOT}` nie działa: reguł uprawnień
Claude Code nie podstawia.

## CHANGELOG

Pełna historia wersji: [CHANGELOG.md](CHANGELOG.md).
