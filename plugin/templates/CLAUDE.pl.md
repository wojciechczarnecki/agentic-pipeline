# CLAUDE.md

Instrukcje dla agentów pracujących z tym repozytorium.

## Projekt

- **TODO: nazwa** — TODO: jedno zdanie, jaki problem rozwiązuje aplikacja
- Właściciel: TODO: imię i nazwisko (TODO: kontakt)
- Stack: TODO: języki, frameworki, baza, narzędzia CI i hosting

## Mapa dokumentów — kiedy co czytać

| Dokument | Kiedy |
|---|---|
| `docs/PROJECT.md` | wizja, wymagania funkcjonalne, architektura — na starcie pracy nad feature'em |
| `docs/ROADMAP.md` | etapy i strumienie, statusy — na starcie każdego zadania; **aktualizuj po ukończeniu** |
| `docs/BACKLOG.md` | odroczone usprawnienia i dług: priorytet P1–P3 + wyzwalacz powrotu |
| `docs/DECISIONS.md` | wiążące decyzje projektowe — zanim zaprojektujesz coś inaczej |
| `docs/CONVENTIONS.md` | styl kodu, testy, git — przy pisaniu kodu |
| `specs/` | SPEC + PLAN per feature — patrz workflow niżej |

## Workflow agentowy

Workflow dostarcza plugin `pipeline`; mechanika (statusy, kontrakt `RESULT`, wyzwalacze
eskalacji, format metryk) jest opisana w jego README — to jedyne źródło prawdy.
Konfiguracja tego projektu dla pluginu żyje w `.claude/workflow.json`.

```
/pipeline:idea (dialog)   → SPEC.md (spec-ready)   ← BRAMKA 1: właściciel zatwierdza SPEC
/pipeline:ship NNN        → plan → recenzja planu → implementacja → raport review
                                                   ← BRAMKA 2: właściciel decyduje o znaleziskach
                          → poprawki, PR, zielone CI, done
merge PR                                           ← BRAMKA 3: właściciel
```

**Fast-path** dla drobiazgów (bugfix, docs, konfiguracja — bez nowych tabel, endpointów
i zależności): mini-plan w rozmowie → implementacja → pełna weryfikacja → `/code-review`
na diffie → decyzje właściciela → PR. W razie wątpliwości → pełny pipeline.

### Zgody na zmiany

- `plan-approved` = zgoda na wszystkie edycje w zakresie planu.
- Poza zakresem planu i w fast-path: przedstaw zamiar i uzyskaj zgodę przed edycją.
- ZAWSZE pytaj przed: migracją na bazie innej niż testowa/deweloperska; usuwaniem plików
  lub danych spoza zakresu planu; dodaniem nowej zależności.

### Git — agent na branchach roboczych, `main` należy do właściciela

Agent sam tworzy branch lane'a, commituje, pushuje i otwiera PR (`gh pr create`).
Branch aktualizuje przez `git merge origin/main` (nie rebase). Poza zasięgiem agenta:
commit, merge i push do `main` (dozwolone tylko `git pull --ff-only`), merge PR,
force-push, `reset --hard`, `clean -f`, `--no-verify`. Egzekwuje to strażnik komend
z pluginu oraz hook `pre-push` (włączany raz na klon:
`git config core.hooksPath scripts/git-hooks`).

## Żelazne zasady

- Każdy feature MUSI mieć testy — bez nich nie jest ukończony.
- TODO: reguła tekstów widocznych dla użytkownika (jedno miejsce na napisy).
- Po ukończeniu zadania odhacz je w `docs/ROADMAP.md` — roadmapa nie może kłamać.
- Decyzje architektoniczne dopisuj do `docs/DECISIONS.md` w tym samym PR.
- Sekrety i dane realnych użytkowników nigdy w kodzie, logach, commitach ani testach.
- Produkcja jest poza zasięgiem sesji agentowych — operacje na niej wykonuje właściciel.

## Komendy

```bash
# TODO: pełna weryfikacja stacku (ta sama komenda co `verify.command` w .claude/workflow.json)
bash scripts/verify.sh

# TODO: uruchomienie aplikacji dewelopersko
# TODO: testy, lint, build per warstwa
```

## Struktura

```
TODO: katalogi projektu i co w nich mieszka
```
