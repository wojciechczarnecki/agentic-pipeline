"""Repository documents: the links they give resolve, and the claims they quote hold.

The root README, CONTRIBUTING.md and SECURITY.md belong to this repository, not to the
plugin, so they are tested here; plugin/tests must keep running from a bare plugin/ checkout.
"""

import json
import os
import re
import subprocess
import sys
import urllib.parse
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


@pytest.mark.parametrize("doc", LINKED)
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


@pytest.mark.parametrize("doc", PLUGIN_DOCUMENTS)
def test_plugin_documents_link_inside_the_plugin(doc):
    document = ROOT / doc
    outside = [
        target
        for target in links(document)
        if not resolve(document, target)[0].is_relative_to(ROOT / "plugin")
    ]
    assert not outside, (doc, outside)


def test_the_link_check_covers_the_six_documents():
    assert [doc for doc in LINKED if (ROOT / doc).is_file()] == LINKED


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


@pytest.mark.parametrize("doc", ROOT_DOCUMENTS)
def test_no_polish_outside_code(doc):
    found = sorted(POLISH & set(strip_code((ROOT / doc).read_text())))
    assert not found, (doc, found)


def read(doc: str) -> str:
    return (ROOT / doc).read_text()


def test_contributing_covers_the_workflow():
    text = read("CONTRIBUTING.md")
    for token in [
        "issue",
        "uv sync",
        "bash scripts/check.sh",
        "core.hooksPath",
        "](docs/CONVENTIONS.md)",
        "main",
        "squash",
        "`plugin`",
        "Polish",
        "Stage 8",
    ]:
        assert token in text, token


def test_security_policy():
    text = read("SECURITY.md")
    for token in [
        "stable",
        "security/advisories/new",
        "best effort",
        "guard bypass",
        "](plugin/docs/GUARD.md#known-limits)",
    ]:
        assert token in text, token
    assert "issues/new" not in text


README = read("README.md")


def section(text: str, heading: str) -> str:
    lines = text.splitlines()
    assert heading in lines, heading
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


def command_lines(text: str) -> list[str]:
    commands, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        command = re.sub(r"\s+#.*$", "", line).strip()
        if fenced and command and not command.startswith("#"):
            commands += [part.strip() for part in re.split(r"&&|\|\||;", command)]
    return commands


def test_command_lines_split_joined_commands():
    block = "```bash\n# note\na && b   # c; d\ne; f\n```\ng && h\n"
    assert command_lines(block) == ["a", "b", "e", "f"]


def fenced_blocks(text: str) -> list[tuple[str, list[str]]]:
    blocks, current, info = [], None, ""
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if current is None:
                current, info = [], line.strip()[3:]
            else:
                blocks.append((info, current))
                current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def paragraphs(text: str) -> list[str]:
    return [
        "\n".join(line for line in chunk.splitlines() if not line.startswith("#"))
        for chunk in strip_fences(text).split("\n\n")
    ]


def test_readme_opens_with_the_display_name_and_the_pitch():
    lines = README.splitlines()
    title = next(index for index, line in enumerate(lines) if line.startswith("# "))
    assert re.fullmatch(r"# Spec-Driven Workflow( [—:-] .+)?", lines[title]), lines[title]
    following = [line for line in lines[title + 1 :] if line.strip()][:5]
    pitches = [
        line
        for line in following
        if not re.search(r"!\[|\[|`", line)
        and "Claude Code" in line
        and line.endswith(".")
        and ". " not in line
    ]
    assert len(pitches) == 1, following


def test_readme_shows_the_three_badges():
    text = urllib.parse.unquote(README)
    assert "actions/workflows/ci.yml/badge.svg" in text
    assert "img.shields.io/badge/license-MIT" in text
    assert (
        "raw.githubusercontent.com/wojciechczarnecki/agentic-pipeline/main/plugin/"
        ".claude-plugin/plugin.json" in text
    )
    assert "query=$.version" in text


GATES = [
    "Gate 1: owner approves the SPEC",
    "Gate 2: owner decides on review findings",
    "Gate 3: owner merges",
]


def test_readme_diagram_names_every_stage_and_gate():
    diagrams = ["\n".join(body) for info, body in fenced_blocks(README) if info == "mermaid"]
    assert len(diagrams) == 1
    for label in ["idea", "plan", "plan review", "implement", "final review", "PR", *GATES]:
        assert label in diagrams[0], label


def test_readme_guard_block_matches_the_guard(tmp_path):
    blocks = [
        body
        for _, body in fenced_blocks(README)
        if body and body[0].startswith("$ git push origin main")
    ]
    assert len(blocks) == 1
    block = blocks[0]
    repo = tmp_path / "repo"
    repo.mkdir()
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    for command in [
        ["git", "init", "-q", "-b", "main"],
        ["git", *identity, "commit", "-q", "--allow-empty", "-m", "init"],
        ["git", "switch", "-q", "-c", "feat/001-x"],
    ]:
        subprocess.run(command, cwd=repo, check=True)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "workflow.json").write_text("{}")
    payload = {
        "tool_input": {"command": block[0].removeprefix("$ ")},
        "cwd": str(repo),
        "session_id": "readme",
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "plugin" / "bin" / "guard.py")],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    )
    assert result.returncode == 2
    assert result.stderr.strip() == "\n".join(block[1:]).strip()


OTHER_TOOLS = re.compile(r"Spec Kit|SpecForge|gate-oriented-sdd")


def test_why_not_spec_kit_states_the_claim_with_dates():
    claim = section(README, "## Why not Spec Kit?")
    for token in ["command guard", "metrics", "SpecForge", "gate-oriented-sdd"]:
        assert token in claim, token
    undated = [
        paragraph
        for paragraph in paragraphs(README)
        if OTHER_TOOLS.search(paragraph) and not re.search(r"checked \d{4}-\d{2}-\d{2}", paragraph)
    ]
    assert not undated, undated


def test_requirements_and_opinions():
    text = section(README, "## Requirements & opinions")
    for token in ["gh", "squash", "rulesets", "python3", "Alembic"]:
        assert token in text, token
    for heading in ["### Who it is for", "### Who it is not for"]:
        assert heading in text.splitlines(), heading


def test_whats_deliberately_not_here():
    text = section(README, "## What's deliberately not here")
    for token in [
        "runtime dependencies",
        "outside Claude Code",
        "best effort",
        "sandbox",
        "](plugin/docs/GUARD.md#known-limits)",
    ]:
        assert token in text, token


def test_readme_install_is_short_and_links_the_guide():
    text = section(README, "## Install")
    assert len(command_lines(text)) <= 3
    assert "](plugin/docs/INSTALL.md)" in text


def test_quickstart_reaches_idea_in_five_commands():
    quickstart = section(README, "## Quickstart")
    assert "](#install)" in quickstart
    install = command_lines(section(README, "## Install"))
    commands = command_lines(quickstart)
    assert len(install) + len(commands) <= 5
    assert commands[-1] == "/pipeline:idea"


def test_readme_explains_the_three_names():
    assert any(
        "Spec-Driven Workflow" in paragraph
        and "`agentic-pipeline`" in paragraph
        and "`pipeline`" in paragraph
        for paragraph in paragraphs(README)
    )


def test_readme_links_the_documentation():
    for link in [
        "](plugin/docs/INSTALL.md)",
        "](plugin/docs/GUARD.md",
        "](plugin/README.md#workflow-metrics)",
        "](CONTRIBUTING.md)",
        "](SECURITY.md)",
        "](plugin/CHANGELOG.md)",
    ]:
        assert link in README, link
