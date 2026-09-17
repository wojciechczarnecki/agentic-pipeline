import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]

# The patterns are assembled from fragments on purpose: this file lives inside the plugin,
# so a literal would be its own match and neither this test nor the raw grep behind it
# could ever pass.
CASE_INSENSITIVE = [
    "logo" + "sowa",
    "pacj" + "ent",
    "neuro" + "logoped",
    "scripts/check" + r"\.sh",
]
# The data-protection acronym is matched only with word boundaries and with case, because
# case-insensitively those four letters hit ordinary Polish words (for example "środowisko").
CASE_SENSITIVE = [r"\b" + "RO" + "DO" + r"\b"]

SKILL_PATHS = ["scripts/check" + r"\.sh", "docs/ROAD" + r"MAP\.md"]
# The init skill documents the default scaffold it writes, so the default document paths
# are its subject matter, not a hardcoded path.
SKILLS_EXEMPT = {"init"}


def files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def hits(path: Path, patterns: list[str], flags: int = 0) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [pattern for pattern in patterns if re.search(pattern, text, flags)]


@pytest.mark.parametrize("path", files(PLUGIN), ids=lambda p: str(p.relative_to(PLUGIN)))
def test_no_project_references(path):
    found = hits(path, CASE_INSENSITIVE, re.IGNORECASE) + hits(path, CASE_SENSITIVE)
    assert not found, (str(path.relative_to(PLUGIN)), found)


@pytest.mark.parametrize(
    "path",
    [p for p in files(PLUGIN / "skills") if p.parent.name not in SKILLS_EXEMPT],
    ids=lambda p: str(p.relative_to(PLUGIN)),
)
def test_skills_have_no_hardcoded_paths(path):
    found = hits(path, SKILL_PATHS)
    assert not found, (str(path.relative_to(PLUGIN)), found)


def test_the_exempt_skill_only_documents_generated_files():
    text = (PLUGIN / "skills" / "init" / "SKILL.md").read_text()
    assert not re.search(SKILL_PATHS[0], text)
    generated = text.split("**Wygeneruj pliki**", 1)[1].split("\n5.", 1)[0]
    for line in text.splitlines():
        if re.search(SKILL_PATHS[1], line):
            assert line in generated, line
