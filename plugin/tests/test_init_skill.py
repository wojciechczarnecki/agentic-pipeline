import os
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "init" / "SKILL.md"
TEMPLATES = PLUGIN / "templates"
TEXT = SKILL.read_text()

GENERATED = {
    ".claude/settings.json": "settings.json",
    ".claude/workflow.json": "workflow.example.json",
    "CLAUDE.md": "CLAUDE.md",
    "docs/PROJECT.md": "docs/PROJECT.md",
    "docs/ROADMAP.md": "docs/ROADMAP.md",
    "docs/BACKLOG.md": "docs/BACKLOG.md",
    "docs/DECISIONS.md": "docs/DECISIONS.md",
    "docs/CONVENTIONS.md": "docs/CONVENTIONS.md",
    "scripts/git-hooks/pre-push": "pre-push",
    ".github/workflows/ci.yml": "github/workflows/ci-placeholder.yml",
    ".github/workflows/security.yml": "github/workflows/security-python.yml",
    ".github/dependabot.yml": "github/dependabot.yml",
}
WRITE_SCOPE = [".claude/", "CLAUDE.md", "docs/", "scripts/", ".github/"]


# The contract is pinned through the identifiers the skill has to name — paths, templates,
# configuration keys — not through its prose, which a rewording (or a translation) would
# break while a change of meaning slipped past. Whether init actually behaves this way is
# measured by the eval cases in plugin/evals.
def step(number: int) -> str:
    start = TEXT.index(f"\n{number}. ")
    end = TEXT.find(f"\n{number + 1}. ", start)
    return TEXT[start : end if end != -1 else len(TEXT)]


def section(heading: str) -> str:
    return TEXT.split(f"## {heading}", 1)[1].split("\n## ", 1)[0]


def test_write_scope_is_declared():
    scope = section("Zakres zapisu (bezwzględny)")
    for prefix in WRITE_SCOPE:
        assert prefix in scope, prefix


def test_configurable_values_are_substituted_into_the_templates():
    generating = step(4)
    assert "gitHooksDir" in generating
    assert "marketplace" in generating
    assert "docs.*" in generating


@pytest.mark.parametrize("generated, template", sorted(GENERATED.items()))
def test_generated_file_list_matches_templates(generated, template):
    assert generated in TEXT, generated
    assert (TEMPLATES / template).is_file(), template


def test_the_git_hook_template_is_executable_and_its_setup_is_printed():
    assert os.access(TEMPLATES / "pre-push", os.X_OK)
    assert "chmod +x" in TEXT
    assert "git config core.hooksPath" in TEXT


def test_ci_variants_are_driven_by_stack_detection():
    assert "ci-python.yml" in TEXT and "ci-node.yml" in TEXT and "ci-placeholder.yml" in TEXT
