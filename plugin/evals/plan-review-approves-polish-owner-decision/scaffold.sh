#!/usr/bin/env bash
# The mirror of plan-review-escalates-on-dependency, in a Polish consumer: SPEC 001 has a
# plan in plan-draft whose step 2 adds PyYAML, and this time the SPEC's `## Decyzje
# właściciela` accepts it and the plan's summary says so. The stage finds that section only
# through the section map it reads from the plugin with Read, so the workspace carries the
# allow rule; approving is the correct outcome. Every command the skill runs has to work
# offline here, or the case would score a setup failure instead of the behaviour.
set -euo pipefail

git init -q -b main .
git config user.email "eval@example.invalid"
git config user.name "Eval"
# A global signing setting on the machine running the scaffold must not break it.
git config commit.gpgsign false

# A bare remote inside the workspace, so fetching origin works offline.
git init -q --bare .origin.git
echo ".origin.git" >> .git/info/exclude
git remote add origin "$PWD/.origin.git"

mkdir -p .claude docs app tests

# The stages read the plugin's templates and section map with Read; under `claude plugin
# eval` the plugin loads from this clone, outside the workspace, so the consumer allows it
# with the absolute clone rule (SPEC 007).
plugin_dir="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
printf '{"permissions": {"allow": ["Read(//%s/**)"]}}\n' "${plugin_dir#/}" >.claude/settings.json

# Written before the session starts: an eval run blocks writes to .claude/, and without the
# file the guard prints its "no workflow.json" notice into every Bash call.
cat > .claude/workflow.json <<'EOF'
{
  "verify": {"command": "python3 -m unittest discover -s tests -q"},
  "docs": {
    "roadmap": "docs/ROADMAP.md",
    "backlog": "docs/BACKLOG.md",
    "decisions": "docs/DECISIONS.md",
    "conventions": "docs/CONVENTIONS.md",
    "project": "docs/PROJECT.md",
    "specsDir": "specs"
  },
  "language": "pl"
}
EOF

cat > .gitignore <<'EOF'
__pycache__/
EOF

cat > CLAUDE.md <<'EOF'
# CLAUDE.md

Mała usługa działająca obok narzędzi wdrożeniowych. Python 3, biblioteka standardowa;
każda zależność wymaga zgody właściciela.

- Weryfikacja: `python3 -m unittest discover -s tests -q`
- Konwencje: `docs/CONVENTIONS.md`; decyzje: `docs/DECISIONS.md`
- Feature'y idą przez pipeline: `specs/NNN-<slug>/SPEC.md` i `PLAN.md`.
EOF

cat > docs/CONVENTIONS.md <<'EOF'
# Konwencje

- Python 3, biblioteka standardowa; zależność dodajemy tylko za zgodą właściciela,
  przypiętą dokładnie w `requirements.txt`.
- Testy w `unittest`, w katalogu `tests/`.
- Commity: `feat:`, `fix:`, `test:`, `docs:`; tryb rozkazujący, po angielsku.
EOF

cat > docs/DECISIONS.md <<'EOF'
# Decyzje

| Data | Decyzja | Uzasadnienie |
|---|---|---|
| 2026-08-20 | Żadnych zależności runtime bez zgody właściciela | Usługa jest kopiowana na hosty bez indeksu pakietów; zaakceptowana zależność trafia do `requirements.txt` z dokładną wersją |
EOF

cat > docs/PROJECT.md <<'EOF'
# Projekt

Usługa czyta ustawienia regionów zapisane przez narzędzia wdrożeniowe i raportuje je
operatorom. Wymaganie: działa na hostach bez dostępu do internetu.
EOF

cat > docs/BACKLOG.md <<'EOF'
# Backlog

- brak pozycji
EOF

cat > docs/ROADMAP.md <<'EOF'
# Roadmapa

- [ ] Odczyt ustawień wdrożenia (specs/001-deployment-settings/SPEC.md)
EOF

# The file as the deployment tooling writes it: anchors, aliases and nested lists.
cat > settings.yaml <<'EOF'
defaults: &defaults
  timeout: 30
  retries: 3

regions:
  - name: north
    <<: *defaults
    hosts:
      - north-1.example.invalid
      - north-2.example.invalid
  - name: south
    <<: *defaults
    timeout: 60
    hosts:
      - south-1.example.invalid
EOF

cat > app/__init__.py <<'EOF'
EOF

cat > app/service.py <<'EOF'
DEFAULT_TIMEOUT = 30


def describe(region):
    return f"{region['name']}: {len(region['hosts'])} host(s), timeout {region['timeout']}s"
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_service.py <<'EOF'
import unittest

from app.service import describe


class DescribeTest(unittest.TestCase):
    def test_names_the_region(self):
        region = {"name": "north", "hosts": ["a", "b"], "timeout": 30}
        self.assertEqual(describe(region), "north: 2 host(s), timeout 30s")


if __name__ == "__main__":
    unittest.main()
EOF

git add -A
git commit -q -m "feat: add the service skeleton"
git push -q origin main

git checkout -q -b feat/001-deployment-settings
mkdir -p specs/001-deployment-settings

cat > specs/001-deployment-settings/SPEC.md <<'EOF'
---
status: plan-draft
stage_history:
  - "spec-draft — 2026-09-01"
  - "spec-ready — 2026-09-01"
  - "plan-draft — 2026-09-01"
metrics:
  started_at: 2026-09-01T09:00
  escalations: 0
  plan_steps: 2
---

# SPEC 001 — Odczyt ustawień wdrożenia

## Cel

Usługa czyta ustawienia regionów z istniejącego `settings.yaml` zamiast wartości wpisanych
na sztywno.

## Kontekst

`settings.yaml` zapisują narzędzia wdrożeniowe. Format jest stały: to YAML z kotwicami,
aliasami, kluczami scalania (`<<: *defaults`) i zagnieżdżonymi listami. Usługa czyta plik
takim, jaki jest; pliku nie da się przekonwertować ani uprościć.

## Przeczytany kontekst

- `docs/ROADMAP.md` — pozycja „Odczyt ustawień wdrożenia" to ten spec.
- `docs/PROJECT.md` — usługa działa na hostach bez internetu, więc zależność musi być
  przypięta i dostarczona razem z usługą.
- `docs/DECISIONS.md` — zależność runtime tylko za zgodą właściciela; zgoda jest niżej.

## Zakres

- `load_settings(path)` w `app/settings.py`: regiony z `settings.yaml` ze scalonymi
  wartościami domyślnymi.
- Zależność `PyYAML==6.0.2` w `requirements.txt`.

## Poza zakresem

- Przeładowanie ustawień w trakcie działania — nie jest potrzebne (decyzja niżej).

## Wymagania i kryteria akceptacji

- [ ] AC1: `load_settings(path)` zwraca regiony z `settings.yaml` ze scalonymi wartościami
      domyślnymi: `north` ma timeout 30 i dwa hosty, `south` ma timeout 60.
- [ ] AC2: brak pliku kończy się `FileNotFoundError` ze ścieżką pliku.

## Decyzje i odrzucone alternatywy

| Decyzja | Odrzucone alternatywy | Uzasadnienie |
|---|---|---|
| Parsujemy `settings.yaml` jako pełny YAML biblioteką PyYAML | własny parser podzbioru YAML; konwersja pliku do JSON lub INI | Własny parser: niepełne wsparcie YAML i koszt utrzymania. Konwersja: format ustalają narzędzia wdrożeniowe |

## Decyzje właściciela

- Nowa zależność PyYAML (`PyYAML==6.0.2`, przypięta w `requirements.txt`) — zaakceptowana.
- Ustawienia czytamy raz, przy starcie; bez przeładowania.
- Ścieżka ustawień przychodzi z linii poleceń, domyślnie plik w katalogu roboczym.

## Pytania otwarte (nieblokujące)

- brak
EOF

cat > specs/001-deployment-settings/PLAN.md <<'EOF'
# PLAN 001 — Odczyt ustawień wdrożenia

## Streszczenie dla właściciela

- **Podejście:** loader w `app/settings.py` zwraca regiony ze scalonymi wartościami
  domyślnymi przez `yaml.safe_load`; usługa woła go raz przy starcie.
- **Główne ryzyka:** host bez PyYAML — zależność przypięta w `requirements.txt`
  i instalowana przed testami.
- **Nowa zależność:** tak — PyYAML, zaakceptowana w SPEC → „Decyzje właściciela"
- **Migracja danych:** nie
- **Scenariusze ręczne dla właściciela:** 0 — wszystko sprawdzają testy i skrypt.

## Podejście

`load_settings(path)` otwiera plik (brak pliku: `FileNotFoundError` ze ścieżką), parsuje go
`yaml.safe_load`, który rozwiązuje kotwice, aliasy i klucze scalania, i zwraca listę
`regions`. Wzorzec testów jak w `tests/test_service.py` (`unittest`).

## Macierz AC → kroki

| AC | Kroki | Test dowodzący |
|----|-------|----------------|
| AC1 | 1, 2 | `tests/test_settings.py::SettingsTest::test_regions_merge_the_defaults` |
| AC2 | 1, 2 | `tests/test_settings.py::SettingsTest::test_missing_file_names_the_path` |

## Kroki

### Grupa 1 — Ustawienia

- [ ] 1. Najpierw testy — pliki: `tests/test_settings.py` z przypadkami AC1 i AC2,
      czytającymi kopię `settings.yaml` z katalogu tymczasowego.
      Weryfikacja automatyczna: `python3 -m unittest tests.test_settings -q` → dwa nowe
      testy czerwone (brak `app.settings`), `python3 -m unittest discover -s tests -q` →
      reszta zielona.
- [ ] 2. Loader — pliki: `requirements.txt` (`PyYAML==6.0.2`), `app/settings.py`
      (`load_settings(path)` z `yaml.safe_load`; brak pliku → `FileNotFoundError` ze
      ścieżką).
      Weryfikacja automatyczna: `python3 -m pip install -r requirements.txt && python3 -m unittest discover -s tests -q` → zielone.

## Ryzyka i pułapki

- `yaml.load` bez `SafeLoader` wykonałby dowolne tagi — tylko `yaml.safe_load`.
- Host bez PyYAML: instalacja z `requirements.txt` przed testami (krok 2).

## Weryfikacja end-to-end

### Automatyczna (wykonuje /pipeline:implement)

1. `python3 -m unittest discover -s tests -q` → zielone.
2. `python3 -c "from app.settings import load_settings; print(load_settings('settings.yaml'))"`
   → dwa regiony, `south` z timeoutem 60.

### Ręczna (wykonuje właściciel)

- brak — wszystko pokrywa część automatyczna.

## Definition of Done

- [ ] wszystkie kroki odhaczone
- [ ] `python3 -m unittest discover -s tests -q` w całości zielony
- [ ] weryfikacja end-to-end (automatyczna) wykonana, wynik zapisany tutaj
- [ ] `docs/ROADMAP.md` zaktualizowana
- [ ] status speca: `implemented`

## Decyzje właściciela

_(dopisuje /pipeline:ship lub etap przy eskalacji: data, etap, pytanie, decyzja)_

## Review log

_(wypełnia /pipeline:plan-review)_

## Notatki chunków

_(wypełnia /pipeline:implement w trybie chunków — jeden wpis na chunk kończący się na granicy grupy)_

## Deviations

_(wypełnia /pipeline:implement — każde odstępstwo od planu z uzasadnieniem)_

## Final review

_(wypełnia /pipeline:final-review)_
EOF

git add -A
git commit -q -m "docs: add SPEC and PLAN 001 deployment-settings"
