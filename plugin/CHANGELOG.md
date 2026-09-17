# CHANGELOG

Wersjonowanie semantyczne. Wydanie znaczone tagiem przez `claude plugin tag`.

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
