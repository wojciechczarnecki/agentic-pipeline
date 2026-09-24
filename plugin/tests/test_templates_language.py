import re
from pathlib import Path

import pytest
from test_readme import POLISH

PLUGIN = Path(__file__).resolve().parents[1]
TEMPLATES = PLUGIN / "templates"
DOCUMENTS = ("SPEC", "PLAN")

# The headings and frontmatter of the inline templates `idea` and `plan` carried before 0.5.0
# (SPEC 006, AC17): a Polish consumer's new specs have to look exactly like its old ones. SPEC 012
# adds two PLAN headings on purpose: the step group heading and the chunk notes section.
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
            "### Grupa N — <nazwa>",
            "## Ryzyka i pułapki",
            "## Weryfikacja end-to-end",
            "### Automatyczna (wykonuje /pipeline:implement)",
            "### Ręczna (wykonuje właściciel)",
            "## Definition of Done",
            "## Decyzje właściciela",
            "## Review log",
            "## Notatki chunków",
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
        "### Group N — <name>",
        "## Risks and traps",
        "## End-to-end verification",
        "### Automatic (performed by /pipeline:implement)",
        "### Manual (performed by the owner)",
        "## Definition of Done",
        "## Owner decisions",
        "## Review log",
        "## Chunk notes",
        "## Deviations",
        "## Final review",
    ],
}

# Every literal pair of the section map (templates/sections.md), including the ones that are
# not headings — stages find sections and summary fields by these strings in specs of either
# language.
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
    ("step-group", "PLAN", "### Grupa N — ", "### Group N — "),
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
    ("chunk-notes", "PLAN", "## Notatki chunków", "## Chunk notes"),
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


# The owner-summary fields (`- **Approach:** …`) are looked up by stages like headings, so the
# structure check covers them too — a field row dropped from the map must break it.
def fields(text: str) -> list[str]:
    return re.findall(r"^- (\*\*[^*\n]+:\*\*)", text, flags=re.MULTILINE)


def frontmatter(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return []
    end = lines.index("---", 1)
    return lines[: end + 1]


def frontmatter_keys(text: str) -> list[str]:
    return [line.split(":", 1)[0] for line in frontmatter(text) if re.match(r"\w+:", line)]


def section_map() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in (TEMPLATES / "sections.md").read_text().splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        # Any other count is a broken map row that would otherwise drop out of every parity
        # check unnoticed.
        assert len(cells) == 4, line
        key, document, polish, english = cells
        rows.append((key.strip("`"), document, polish[1:-1], english[1:-1]))
    return rows


def rows(document: str, table=None) -> list[tuple[str, str, str, str]]:
    return [row for row in (section_map() if table is None else table) if row[1] == document]


# A literal that ends in "— " is a prefix (`### Group N — <name>`); every other one matches
# exactly.
def matches_literal(heading: str, literal: str) -> bool:
    if literal.endswith("— "):
        return heading.startswith(literal)
    return heading == literal


def key_of(heading: str, document: str, column: int, table=None) -> str:
    matches = [row[0] for row in rows(document, table) if matches_literal(heading, row[column])]
    assert len(matches) == 1, (document, heading)
    return matches[0]


def check_structure(document: str, table=None) -> None:
    polish, english = template(document, "pl"), template(document, "en")
    structure = {}
    for language, text, column in (("pl", polish, 2), ("en", english, 3)):
        lines = headings(text)
        assert lines[0].startswith(f"# {document} NNN — "), (language, lines[0])
        structure[language] = [
            (line.split(" ", 1)[0], key_of(line, document, column, table)) for line in lines[1:]
        ] + [("field", key_of(field, document, column, table)) for field in fields(text)]
    assert structure["pl"] == structure["en"]
    assert frontmatter_keys(polish) == frontmatter_keys(english)


def check_occurs(document: str, table=None) -> None:
    polish, english = template(document, "pl"), template(document, "en")
    for key, _, polish_literal, english_literal in rows(document, table):
        assert polish_literal in polish, (key, polish_literal)
        assert english_literal in english, (key, english_literal)


def check_unique_keys(document: str, table=None) -> None:
    keys = [row[0] for row in rows(document, table)]
    assert len(keys) == len(set(keys))


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
    check_structure(document)


# SPEC 010, AC1: the AC matrix carries the red record `implement` fills in, in both languages,
# as a table column, so the section map stays as it is.
@pytest.mark.parametrize(
    "language, header",
    [
        ("en", "| AC | Steps | Proving test | Red before the change |"),
        ("pl", "| AC | Kroki | Test dowodzący | Czerwony przed zmianą |"),
    ],
)
def test_the_ac_matrix_has_the_red_column(language, header):
    lines = template("PLAN", language).splitlines()
    assert header in lines, (language, header)
    separator = lines[lines.index(header) + 1]
    assert re.fullmatch(r"\|(-+\|)+", separator), separator
    assert separator.count("|") == 5, separator


@pytest.mark.parametrize("document", DOCUMENTS)
def test_every_map_row_occurs_in_its_template(document):
    check_occurs(document)


@pytest.mark.parametrize("name", ENGLISH_TEMPLATES)
def test_english_templates_have_no_polish(name):
    # Unstripped: the English templates carry no Polish even in code, and a fence left open
    # would otherwise hide the rest of the file.
    found = sorted(POLISH & set((TEMPLATES / name).read_text()))
    assert not found, (name, found)


@pytest.mark.parametrize("document", DOCUMENTS)
def test_map_keys_are_unique_per_document(document):
    check_unique_keys(document)


def test_the_section_map_is_well_formed():
    table = section_map()
    assert {document for _, document, _, _ in table} == {"SPEC", "PLAN"}
    for line in (TEMPLATES / "sections.md").read_text().splitlines():
        if line.startswith("| `"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            for cell in cells[2:]:
                assert re.fullmatch(r"`[^`]+`", cell), line
    for _, _, _, english in table:
        assert not POLISH & set(english), english


# AC2: the parity checks are only worth something if a row missing from the map breaks them.
@pytest.mark.parametrize(
    "document, dropped", [("SPEC", "owner-decisions"), ("PLAN", "summary-dependency")]
)
def test_the_parity_checks_miss_a_removed_row(document, dropped):
    table = [row for row in section_map() if not (row[1] == document and row[0] == dropped)]
    assert len(table) == len(section_map()) - 1
    failed = 0
    for check in (check_structure, check_occurs):
        try:
            check(document, table)
        except AssertionError:
            failed += 1
    assert failed, dropped
    duplicated = section_map() + [next(r for r in section_map() if r[1] == document)]
    with pytest.raises(AssertionError):
        check_unique_keys(document, duplicated)
