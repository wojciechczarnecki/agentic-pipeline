import re
from pathlib import Path

import pytest
from test_readme import POLISH, section_map, strip_code

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

ENGLISH_TEMPLATES = ["SPEC.en.md", "PLAN.en.md"]


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
    found = sorted(POLISH & set(strip_code((TEMPLATES / name).read_text())))
    assert not found, (name, found)


@pytest.mark.parametrize("document", DOCUMENTS)
def test_map_keys_are_unique_per_document(document):
    keys = [row[0] for row in rows(document)]
    assert len(keys) == len(set(keys))
