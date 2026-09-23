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

from test_english_only import POLISH_LETTERS as POLISH  # noqa: E402
from test_english_only import polish_files, polish_in_python_names  # noqa: E402
from test_no_domain_references import CASE_INSENSITIVE, CASE_SENSITIVE  # noqa: E402

LINKED = [
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "plugin/README.md",
    "plugin/docs/INSTALL.md",
    "plugin/docs/GUARD.md",
    "plugin/docs/NEW-PROJECT.md",
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
    assert slug("What sets it apart") == "what-sets-it-apart"
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


@pytest.mark.parametrize("doc", ROOT_DOCUMENTS)
def test_no_polish_outside_code(doc):
    found = sorted(POLISH & set(strip_code((ROOT / doc).read_text())))
    assert not found, (doc, found)


# SPEC 008, AC2 and AC3 for the repository's own tests: no allowlist, nothing here pins a
# Polish file as data.
def test_repository_tests_are_english():
    assert polish_files(ROOT / "tests") == []


@pytest.mark.parametrize("path", sorted((ROOT / "tests").glob("*.py")), ids=lambda p: p.name)
def test_repository_test_code_is_english(path):
    assert not polish_in_python_names(path)


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
        "sections.md",
    ]:
        assert token in text, token


def markdown_section(text: str, heading: str) -> str:
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


# SPEC 008, AC9: the documents say where Polish lives.
def test_conventions_state_english_skills():
    language = markdown_section(read("docs/CONVENTIONS.md"), "## Language")
    for token in ["*.pl.md", "sections.md", "skills", "agents", "test_english_only.py"]:
        assert token in language, token
    assert "until translated" not in language


def test_decisions_record_the_translation():
    rows = [line for line in read("docs/DECISIONS.md").splitlines() if "SPEC 008" in line]
    assert any("2026-09-17" in row and "2026-09-21" in row for row in rows), rows


def test_roadmap_ticks_the_translation():
    items = re.split(r"\n(?=- \[)", read("docs/ROADMAP.md"))
    item = [item for item in items if "translated into English" in item]
    assert len(item) == 1, item
    assert item[0].startswith("- [x]")
    assert "specs/008-translate-skills-to-english/SPEC.md" in item[0]


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


# A deliberate copy of `command_count` in plugin/tests/test_readme.py (no cross-directory import
# of test modules, PLAN 003 Approach): a change to how commands are counted goes into both.
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


LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def paragraphs(text: str) -> list[str]:
    """Blank-line paragraphs with heading lines dropped; every list item is a unit of its own."""
    units = []
    for chunk in strip_fences(text).split("\n\n"):
        current: list[str] = []
        for line in chunk.splitlines():
            if line.startswith("#"):
                continue
            if LIST_ITEM.match(line) and current:
                units.append("\n".join(current))
                current = []
            current.append(line)
        units.append("\n".join(current))
    return units


def test_paragraphs_split_list_items():
    text = "# Title\nIntro line\n- one\n  more\n- two\n\nNext paragraph\n"
    assert paragraphs(text) == ["Intro line", "- one\n  more", "- two", "Next paragraph"]


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
    # exact node labels: a substring match finds "plan" inside "plan review"
    labels = set(re.findall(r'"([^"]+)"', diagrams[0]))
    for label in ["idea", "plan", "plan review", "implement", "final review", "PR", *GATES]:
        assert label in labels, label


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
    # A consumer set up as documented: the Read rule for the plugin keeps the guard's
    # once-per-session notice (SPEC 007) out of the refusal the README quotes.
    plugin = str(ROOT / "plugin").lstrip("/")
    (repo / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": [f"Read(//{plugin}/**)"]}})
    )
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


def test_what_sets_it_apart_names_no_other_tool():
    claim = section(README, "## What sets it apart")
    for token in ["command guard", "metrics:"]:
        assert token in claim, token
    assert not OTHER_TOOLS.search(README), OTHER_TOOLS.search(README)


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


INSTALL_GUIDE = read("plugin/docs/INSTALL.md")


def test_readme_install_is_short_and_links_the_guide():
    text = section(README, "## Install")
    commands = command_lines(text)
    assert len(commands) <= 3
    assert "](plugin/docs/INSTALL.md)" in text
    # the short section is the guide's own path, on the release channel and the user scope
    assert any("#stable" in command for command in commands), commands
    assert any("--scope user" in command for command in commands), commands
    missing = [command for command in commands if command not in INSTALL_GUIDE]
    assert not missing, missing


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


def test_the_new_project_guide_is_linked():
    assert "](docs/NEW-PROJECT.md)" in section(read("plugin/README.md"), "## Installation")
    assert "](NEW-PROJECT.md)" in INSTALL_GUIDE


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


CONVENTIONS = read("docs/CONVENTIONS.md")


# A minor or major release runs the unreleased plugin in a consumer before it is tagged;
# the step has no mechanism behind it, so the procedure text is what keeps it.
def test_release_procedure_runs_the_canary_before_the_tag():
    releases = section(CONVENTIONS, "## Releases")
    assert releases.index("canary") < releases.index("claude plugin tag")
    bullet = next(unit for unit in releases.split("\n- ") if "canary" in unit)
    for token in ["--plugin-dir", "patch", "minor or major", "overrides installed version"]:
        assert token in bullet, token


# SPEC 007, AC15: a canary loads the plugin from a clone, which the cache rule does not
# cover, so the procedure names the absolute clone rule.
def test_the_canary_names_the_clone_read_rule():
    releases = section(CONVENTIONS, "## Releases")
    assert "Read(//" in releases


def test_claude_md_lists_the_canary():
    commands = [body for info, body in fenced_blocks(read("CLAUDE.md")) if info == "bash"]
    lines = "\n".join(commands[0]).splitlines()
    tag = next(i for i, line in enumerate(lines) if "claude plugin tag" in line)
    canary = [
        i for i, line in enumerate(lines) if "--plugin-dir" in line and "--debug-file" in line
    ]
    assert canary and canary[0] < tag


def test_conventions_state_the_eval_cost_policy():
    tests = section(CONVENTIONS, "## Tests")
    for token in ["runs: 3", "--model sonnet", "default model", "--max-cost-usd", "majority"]:
        assert token in tests, token


ROADMAP = read("docs/ROADMAP.md")


# Stage 8 runs before Stage 6 and keeps its number, because append-only rows in
# docs/DECISIONS.md refer to stages by number ("until Stage 8").
def test_roadmap_stage_order():
    stages = [int(n) for n in re.findall(r"^## Stage (\d+)\b", ROADMAP, re.M)]
    assert stages == [1, 2, 3, 4, 5, 8, 6, 7, 9]


def test_roadmap_release_versions_ascend():
    versions = [
        tuple(int(part) for part in match.split("."))
        for match in re.findall(r"^\s*- \[[ x]\] (\d+\.\d+\.\d+)", ROADMAP, re.M)
    ]
    assert versions and versions == sorted(versions)


# SPEC 005, AC20: `stable` is kept off by the guard's protectedBranches, not by deny rules.
@pytest.mark.parametrize("doc", ["CLAUDE.md", "docs/CONVENTIONS.md"])
def test_claude_md_and_conventions_name_protected_branches(doc):
    text = " ".join(read(doc).split())
    assert "protectedBranches" in text
    for stale in [
        "kept off it by `deny` rules",
        "`deny` rules on `git push` to",
        "the guard protects `main`/`master` only",
    ]:
        assert stale not in text, stale


# SPEC 005, AC19: the guard (0.4.0) keeps agents off `stable` and off detaching the plugin,
# so only the rules it does not cover stay in `deny`.
def test_repository_settings_leave_stable_and_detaching_to_the_guard():
    settings = json.loads(read(".claude/settings.json"))
    assert settings["permissions"]["deny"] == ["Bash(gh pr merge*)", "Bash(claude plugin enable*)"]
    workflow = json.loads(read(".claude/workflow.json"))
    assert workflow["protectedBranches"] == ["stable"]


# SPEC 007, AC16: the run-time reads reverse the inline-template decision in the register.
def test_decisions_record_run_time_reads():
    rows = [line for line in read("docs/DECISIONS.md").splitlines() if line.startswith("| ")]
    assert any("templates/sections.md" in row and "Read(" in row for row in rows)


# SPEC 007, AC6: sessions here run the released plugin from the install cache, and its stages
# read their templates from there with Read; a stage subagent cannot answer the prompt.
def test_repository_settings_allow_reading_the_installed_plugin():
    settings = json.loads(read(".claude/settings.json"))
    assert "Read(~/.claude/plugins/cache/wcz-tools/pipeline/**)" in settings["permissions"]["allow"]
