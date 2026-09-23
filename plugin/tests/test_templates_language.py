import re
from pathlib import Path

import pytest
from test_readme import POLISH, section_map

PLUGIN = Path(__file__).resolve().parents[1]
TEMPLATES = PLUGIN / "templates"
DOCUMENTS = ("SPEC", "PLAN")

# The headings and frontmatter of the inline templates `idea` and `plan` carried before 0.5.0
# (SPEC 006, AC17): a Polish consumer's new specs have to look exactly like its old ones.
POLISH_SNAPSHOT = {
    "SPEC": {
        "frontmatter": [
            "---",
            "status: spec-draft",
            "stage_history:",
            '  - "spec-draft — YYYY-MM-DD"',
            "---",
        ],
        "headings": [
            "# SPEC NNN — <nazwa feature'a>",
            "## Cel",
            "## Kontekst",
            "## Przeczytany kontekst",
            "## Zakres",
            "## Poza zakresem",
            "## Wymagania i kryteria akceptacji",
            "## Decyzje i odrzucone alternatywy",
            "## Decyzje właściciela",
            "## Pytania otwarte (nieblokujące)",
        ],
    },
    "PLAN": {
        "frontmatter": [],
        "headings": [
            "# PLAN NNN — <nazwa feature'a>",
            "## Streszczenie dla właściciela",
            "## Podejście",
            "## Macierz AC → kroki",
            "## Kroki",
            "## Ryzyka i pułapki",
            "## Weryfikacja end-to-end",
            "### Automatyczna (wykonuje /pipeline:implement)",
            "### Ręczna (wykonuje właściciel)",
            "## Definition of Done",
            "## Decyzje właściciela",
            "## Review log",
            "## Deviations",
            "## Final review",
        ],
    },
}

# The English headings the specs written here before 0.5.0 already use (SPEC 006, AC6): a
# rename made in the template, the inline block and the map together would keep every parity
# check green while those specs stopped matching, so the headings are pinned on their own.
ENGLISH_HEADINGS = {
    "SPEC": [
        "# SPEC NNN — <feature name>",
        "## Goal",
        "## Context",
        "## Read context",
        "## Scope",
        "## Out of scope",
        "## Requirements and acceptance criteria",
        "## Decisions and rejected alternatives",
        "## Owner decisions",
        "## Open questions (non-blocking)",
    ],
    "PLAN": [
        "# PLAN NNN — <feature name>",
        "## Owner summary",
        "## Approach",
        "## AC → steps matrix",
        "## Steps",
        "## Risks and traps",
        "## End-to-end verification",
        "### Automatic (performed by /pipeline:implement)",
        "### Manual (performed by the owner)",
        "## Definition of Done",
        "## Owner decisions",
        "## Review log",
        "## Deviations",
        "## Final review",
    ],
}

# Every literal pair of the README section map, including the ones that are not headings —
# stages find sections and summary fields by these strings in specs of either language.
MAP_SNAPSHOT = [
    ("goal", "SPEC", "## Cel", "## Goal"),
    ("context", "SPEC", "## Kontekst", "## Context"),
    ("read-context", "SPEC", "## Przeczytany kontekst", "## Read context"),
    ("scope", "SPEC", "## Zakres", "## Scope"),
    ("out-of-scope", "SPEC", "## Poza zakresem", "## Out of scope"),
    (
        "requirements",
        "SPEC",
        "## Wymagania i kryteria akceptacji",
        "## Requirements and acceptance criteria",
    ),
    (
        "decisions",
        "SPEC",
        "## Decyzje i odrzucone alternatywy",
        "## Decisions and rejected alternatives",
    ),
    ("owner-decisions", "SPEC", "## Decyzje właściciela", "## Owner decisions"),
    (
        "open-questions",
        "SPEC",
        "## Pytania otwarte (nieblokujące)",
        "## Open questions (non-blocking)",
    ),
    ("assumption", "SPEC", "(założenie)", "(assumption)"),
    ("owner-summary", "PLAN", "## Streszczenie dla właściciela", "## Owner summary"),
    ("summary-approach", "PLAN", "**Podejście:**", "**Approach:**"),
    ("summary-risks", "PLAN", "**Główne ryzyka:**", "**Main risks:**"),
    ("summary-dependency", "PLAN", "**Nowa zależność:**", "**New dependency:**"),
    ("summary-migration", "PLAN", "**Migracja danych:**", "**Data migration:**"),
    (
        "summary-manual",
        "PLAN",
        "**Scenariusze ręczne dla właściciela:**",
        "**Manual scenarios for the owner:**",
    ),
    ("approach", "PLAN", "## Podejście", "## Approach"),
    ("ac-matrix", "PLAN", "## Macierz AC → kroki", "## AC → steps matrix"),
    ("steps", "PLAN", "## Kroki", "## Steps"),
    ("step-verification", "PLAN", "Weryfikacja automatyczna:", "Automatic verification:"),
    ("risks", "PLAN", "## Ryzyka i pułapki", "## Risks and traps"),
    ("e2e", "PLAN", "## Weryfikacja end-to-end", "## End-to-end verification"),
    (
        "e2e-automatic",
        "PLAN",
        "### Automatyczna (wykonuje /pipeline:implement)",
        "### Automatic (performed by /pipeline:implement)",
    ),
    (
        "e2e-manual",
        "PLAN",
        "### Ręczna (wykonuje właściciel)",
        "### Manual (performed by the owner)",
    ),
    ("definition-of-done", "PLAN", "## Definition of Done", "## Definition of Done"),
    ("owner-decisions", "PLAN", "## Decyzje właściciela", "## Owner decisions"),
    ("review-log", "PLAN", "## Review log", "## Review log"),
    ("deviations", "PLAN", "## Deviations", "## Deviations"),
    ("final-review", "PLAN", "## Final review", "## Final review"),
]

ENGLISH_TEMPLATES = [
    "SPEC.en.md",
    "PLAN.en.md",
    "CLAUDE.en.md",
    "docs/PROJECT.en.md",
    "docs/ROADMAP.en.md",
    "docs/BACKLOG.en.md",
    "docs/DECISIONS.en.md",
    "docs/CONVENTIONS.en.md",
]


def template(document: str, language: str) -> str:
    return (TEMPLATES / f"{document}.{language}.md").read_text()


def headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"#+ ", line)]


def frontmatter(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return []
    end = lines.index("---", 1)
    return lines[: end + 1]


def frontmatter_keys(text: str) -> list[str]:
    return [line.split(":", 1)[0] for line in frontmatter(text) if re.match(r"\w+:", line)]


def rows(document: str) -> list[tuple[str, str, str, str]]:
    return [row for row in section_map() if row[1] == document]


def key_of(heading: str, document: str, column: int) -> str:
    matches = [row[0] for row in rows(document) if row[column] == heading]
    assert len(matches) == 1, (document, heading)
    return matches[0]


@pytest.mark.parametrize("document", DOCUMENTS)
def test_polish_templates_match_the_snapshot(document):
    text = template(document, "pl")
    assert headings(text) == POLISH_SNAPSHOT[document]["headings"]
    assert frontmatter(text) == POLISH_SNAPSHOT[document]["frontmatter"]


@pytest.mark.parametrize("document", DOCUMENTS)
def test_english_templates_match_the_snapshot(document):
    assert headings(template(document, "en")) == ENGLISH_HEADINGS[document]


def test_the_section_map_matches_the_snapshot():
    assert section_map() == MAP_SNAPSHOT


@pytest.mark.parametrize("document", DOCUMENTS)
def test_template_pairs_have_the_same_structure(document):
    polish, english = template(document, "pl"), template(document, "en")
    structure = {}
    for language, text, column in (("pl", polish, 2), ("en", english, 3)):
        lines = headings(text)
        assert lines[0].startswith(f"# {document} NNN — "), (language, lines[0])
        structure[language] = [
            (line.split(" ", 1)[0], key_of(line, document, column)) for line in lines[1:]
        ]
    assert structure["pl"] == structure["en"]
    assert frontmatter_keys(polish) == frontmatter_keys(english)


@pytest.mark.parametrize("document", DOCUMENTS)
def test_every_map_row_occurs_in_its_template(document):
    polish, english = template(document, "pl"), template(document, "en")
    for key, _, polish_literal, english_literal in rows(document):
        assert polish_literal in polish, (key, polish_literal)
        assert english_literal in english, (key, english_literal)


@pytest.mark.parametrize("name", ENGLISH_TEMPLATES)
def test_english_templates_have_no_polish(name):
    # Unstripped: the English templates carry no Polish even in code, and a fence left open
    # would otherwise hide the rest of the file.
    found = sorted(POLISH & set((TEMPLATES / name).read_text()))
    assert not found, (name, found)


@pytest.mark.parametrize("document", DOCUMENTS)
def test_map_keys_are_unique_per_document(document):
    keys = [row[0] for row in rows(document)]
    assert len(keys) == len(set(keys))
