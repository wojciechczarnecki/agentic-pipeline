"""Repository documents: the links they give resolve, and the claims they quote hold.

The root README, CONTRIBUTING.md and SECURITY.md belong to this repository, not to the
plugin, so they are tested here; plugin/tests must keep running from a bare plugin/ checkout.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin" / "tests"))

from test_no_domain_references import CASE_INSENSITIVE, CASE_SENSITIVE  # noqa: E402

LINKED = [
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "plugin/README.md",
    "plugin/docs/INSTALL.md",
    "plugin/docs/GUARD.md",
]
PLUGIN_DOCUMENTS = [doc for doc in LINKED if doc.startswith("plugin/")]
ROOT_DOCUMENTS = ["README.md", "CONTRIBUTING.md", "SECURITY.md"]

LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
EXTERNAL = ("http://", "https://", "mailto:")


def existing(documents: list[str]) -> list[str]:
    return [doc for doc in documents if (ROOT / doc).exists()]


def strip_fences(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return "\n".join(kept)


def strip_code(text: str) -> str:
    return re.sub(r"`[^`\n]*`", "", strip_fences(text))


def slug(heading: str) -> str:
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    found: set[str] = set()
    for line in strip_fences(path.read_text()).splitlines():
        match = re.match(r"#{1,6} (.+)$", line)
        if not match:
            continue
        base = slug(match.group(1))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def links(path: Path) -> list[str]:
    text = strip_code(path.read_text())
    return [target for target in LINK.findall(text) if not target.startswith(EXTERNAL)]


def resolve(document: Path, target: str) -> tuple[Path, str]:
    location, _, anchor = target.partition("#")
    resolved = document if not location else (document.parent / location).resolve()
    return resolved, anchor


def test_github_anchor_slugs():
    assert slug("Known limits") == "known-limits"
    assert slug("Requirements & opinions") == "requirements--opinions"
    assert slug("Why not Spec Kit?") == "why-not-spec-kit"
    assert (
        slug("Project configuration — `.claude/workflow.json`")
        == "project-configuration--claudeworkflowjson"
    )


def test_repeated_headings_get_numbered_anchors(tmp_path):
    document = tmp_path / "doc.md"
    document.write_text("# Title\n\n## Usage\n\n## Usage\n\n```\n## Not a heading\n```\n")
    assert anchors(document) == {"title", "usage", "usage-1"}


@pytest.mark.parametrize("doc", existing(LINKED))
def test_relative_links_resolve(doc):
    document = ROOT / doc
    broken = []
    for target in links(document):
        resolved, anchor = resolve(document, target)
        if not resolved.exists():
            broken.append(target)
        elif anchor and resolved.suffix == ".md" and anchor not in anchors(resolved):
            broken.append(target)
    assert not broken, (doc, broken)


@pytest.mark.parametrize("doc", existing(PLUGIN_DOCUMENTS))
def test_plugin_documents_link_inside_the_plugin(doc):
    document = ROOT / doc
    outside = [
        target
        for target in links(document)
        if not resolve(document, target)[0].is_relative_to(ROOT / "plugin")
    ]
    assert not outside, (doc, outside)


@pytest.mark.xfail(strict=True, reason="the root documents arrive in steps 2-4")
def test_the_link_check_covers_the_six_documents():
    assert existing(LINKED) == LINKED


def markdown_files() -> list[Path]:
    excluded = {"plugin", ".venv", ".git", "node_modules"}
    return [
        path
        for path in sorted(ROOT.rglob("*.md"))
        if not any(
            part in excluded or part.startswith(".") for part in path.relative_to(ROOT).parts[:-1]
        )
    ]


# The fragments come from the plugin's own test so there is no third copy of the list; the
# check-script path is a plugin-only rule, and repository documents name it legitimately.
CONSUMER_PATTERNS = [pattern for pattern in CASE_INSENSITIVE if "scripts/check" not in pattern]


@pytest.mark.parametrize("path", markdown_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_document_names_the_private_consumer(path):
    text = path.read_text(encoding="utf-8")
    found = [p for p in CONSUMER_PATTERNS if re.search(p, text, re.IGNORECASE)]
    found += [p for p in CASE_SENSITIVE if re.search(p, text)]
    assert not found, (str(path.relative_to(ROOT)), found)


POLISH = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


@pytest.mark.parametrize("doc", existing(ROOT_DOCUMENTS))
def test_no_polish_outside_code(doc):
    found = sorted(POLISH & set(strip_code((ROOT / doc).read_text())))
    assert not found, (doc, found)
