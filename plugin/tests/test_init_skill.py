import os
import re
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


# The contract is pinned through structural anchors — the numbered steps and the named
# sections of the skill — not through prose that a rewording would break and a change of
# meaning could slip past. Whether init actually behaves this way is measured by the eval
# cases in plugin/evals (init-keeps-manual-edits, init-without-questions).
def step(number: int) -> str:
    start = TEXT.index(f"\n{number}. ")
    end = TEXT.find(f"\n{number + 1}. ", start)
    return TEXT[start : end if end != -1 else len(TEXT)]


def section(heading: str) -> str:
    return TEXT.split(f"## {heading}", 1)[1].split("\n## ", 1)[0]


def test_first_round_is_capped():
    questions_step = step(2)
    assert re.search(r"maksymalnie 4|max(imum)? 4|maks\. 4", questions_step)
    questions = re.findall(r"^[ \t]+\d+\. ", questions_step, re.MULTILINE)
    assert 1 <= len(questions) <= 4, questions
    assert "Druga runda" in questions_step


def test_non_interactive_contract():
    non_interactive = step(3)
    assert "claude -p" in non_interactive
    assert "TODO:" in non_interactive
    assert re.search(r"NIE pytasz i NIE\s+blokujesz", non_interactive)


def test_write_scope_and_overwrite_rule():
    scope = section("Zakres zapisu (bezwzględny)")
    for prefix in WRITE_SCOPE:
        assert prefix in scope, prefix
    assert "Nic poza tymi prefiksami" in scope
    existing = step(5)
    assert "ZAPYTAJ przed" in existing and "NIGDY nie nadpisujesz" in existing
    assert "pominiętych" in existing


def test_idempotency_rules():
    idempotency = step(6)
    assert "Idempotencja" in idempotency
    assert "zostaje nietknięta" in idempotency
    assert "NOWYCH odpowiedzi" in idempotency
    assert "git status" in idempotency


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


def test_generated_settings_carry_no_duplicate_hooks():
    assert "Bez sekcji `hooks`" in TEXT


def test_ci_variants_are_driven_by_stack_detection():
    assert "ci-python.yml" in TEXT and "ci-node.yml" in TEXT and "ci-placeholder.yml" in TEXT
    assert "oba → OBA joby" in TEXT
    assert "`github-actions` zostaje ZAWSZE" in TEXT
