import json
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
    "CLAUDE.md": "CLAUDE.{language}.md",
    "docs/PROJECT.md": "docs/PROJECT.{language}.md",
    "docs/ROADMAP.md": "docs/ROADMAP.{language}.md",
    "docs/BACKLOG.md": "docs/BACKLOG.{language}.md",
    "docs/DECISIONS.md": "docs/DECISIONS.{language}.md",
    "docs/CONVENTIONS.md": "docs/CONVENTIONS.{language}.md",
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


def settings_bullet(text: str) -> str:
    start = text.index("- `.claude/settings.json`")
    rest = text[start + 1 :]
    end = rest.find("\n   - `")
    return rest[: end if end != -1 else len(rest)]


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
@pytest.mark.parametrize("language", ["en", "pl"])
def test_generated_file_list_matches_templates(generated, template, language):
    assert generated in TEXT, generated
    source = template.format(language=language)
    assert (TEMPLATES / source).is_file(), source


def test_the_git_hook_template_is_executable_and_its_setup_is_printed():
    assert os.access(TEMPLATES / "pre-push", os.X_OK)
    assert "chmod +x" in TEXT
    assert "git config core.hooksPath" in TEXT


def test_ci_variants_are_driven_by_stack_detection():
    assert "ci-python.yml" in TEXT and "ci-node.yml" in TEXT and "ci-placeholder.yml" in TEXT


# The consumer's settings must not carry a `hooks` block of its own: the plugin already
# registers the format and notify hooks, and a copy in the project would fire them twice.
def test_the_settings_template_registers_no_hooks():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    assert "hooks" not in settings


# `github-actions` is stack-independent, so it stays in dependabot.yml for every project,
# whichever CI variant the skill picks.
def test_the_dependabot_template_covers_github_actions():
    ecosystems = [
        line.split(":", 1)[1].strip()
        for line in (TEMPLATES / "github" / "dependabot.yml").read_text().splitlines()
        if line.strip().startswith("- package-ecosystem:")
    ]
    assert "github-actions" in ecosystems


# AC27/AC28: the marketplace name is still derived from ${CLAUDE_PLUGIN_ROOT}, but `ref`
# is the `stable` channel, not a tag built from the version in that path — a tag pin
# forces the marketplace to be re-registered, and the plugin reinstalled in every
# project, on each release (docs/DECISIONS.md, 2026-09-21). The skill's wording is not
# pinned, only the literal: step 4 substitutes the source itself, so the template test
# (test_init_templates.py) cannot tell which `ref` init writes.
def test_the_marketplace_ref_is_the_stable_channel():
    block = " ".join(settings_bullet(step(4)).split())
    sentences = block.split(". ")
    derivation = [sentence for sentence in sentences if "CLAUDE_PLUGIN_ROOT" in sentence]
    assert derivation, "init step 4 must derive the marketplace name from ${CLAUDE_PLUGIN_ROOT}"
    channel = [
        sentence for sentence in sentences if "`ref`" in sentence and '`"stable"`' in sentence
    ]
    assert channel, 'init step 4 must set `ref` to the literal `"stable"`'
    assert "<plugin>--v<wersja>" not in block, "init step 4 must not build a tag pin"
    fallback = [sentence for sentence in sentences if "TODO:" in sentence and "kszta" in sentence]
    assert fallback, "init step 4 must keep the `TODO:` fallback for an unexpected path shape"


# The settings file init writes declares the marketplace but never enables the plugin:
# `enabledPlugins: true` makes every session there install a `--scope project` duplicate
# that `plugin update --scope user` leaves behind (docs/DECISIONS.md, 2026-09-21).
def test_the_settings_file_does_not_enable_the_plugin():
    block = settings_bullet(step(4))
    assert "extraKnownMarketplaces" in block
    assert "**Bez `enabledPlugins`**" in block, "init step 4 must forbid `enabledPlugins`"
    assert "i w `enabledPlugins`" not in block


# A rule the model can reach only after it has already been told to ask is a rule it will
# weigh rather than follow: measured 2026-09-20, two eval runs of the same commit split,
# one finishing the skill and one asking four questions in prose and waiting. The guard is
# therefore that step 2 itself names the absent tool and sends the reader to step 3, and
# that the prose loophole is closed in both places.
def test_the_question_step_checks_for_the_tool_before_asking():
    asking = step(2)
    head = asking[: asking.index("1. ")]
    assert "AskUserQuestion" in head, (
        "init step 2 must open by checking for AskUserQuestion, before it tells the "
        "reader to ask anything"
    )
    assert "3" in head, "init step 2 must send a reader without the tool to step 3"


@pytest.mark.parametrize("number", [2, 3])
def test_the_non_interactive_mode_forbids_asking_in_prose(number):
    body = " ".join(step(number).split())
    assert "tekst" in body or "prozą" in body, (
        f"init step {number} must close the prose loophole: without AskUserQuestion the "
        "skill may not ask in plain text either"
    )


# workflow.example.json shows `protectedBranches`, and init builds workflow.json from it;
# the release channel is the owner's to configure, so step 4 has to name the key it leaves
# out (SPEC 005, AC7).
def test_init_does_not_write_protected_branches():
    assert "protectedBranches" in step(4)


def questions() -> list[str]:
    asking = step(2)
    return re.findall(r"\n   (\d)\. (.*(?:\n      .*)*)", asking)


# SPEC 006, AC10: the language comes first, because it decides every document init writes;
# `en` is the recommended default.
def test_the_language_is_the_first_question():
    found = questions()
    assert 1 <= len(found) <= 4, found
    number, first = found[0]
    assert number == "1"
    for token in ["`language`", "`en`", "`pl`", "(Recommended)"]:
        assert token in first, token


# SPEC 006, AC12: unattended, the argument names the language or it is `en`, without a
# `TODO:` marker — the prompt's own language does not count.
def test_unattended_language_comes_from_the_argument():
    body = " ".join(step(3).split())
    for token in ["argument", "`en`", "`pl`", "`language`"]:
        assert token in body, token


# SPEC 006, AC11: every document is copied from the template of the chosen language.
def test_templates_are_picked_by_language():
    generating = step(4)
    assert "templates/CLAUDE.<language>.md" in generating
    assert "templates/docs/<NAZWA>.<language>.md" in generating
    assert "templates/CLAUDE.md" not in generating


# SPEC 006, AC13: a re-run with another language changes the key, not the documents.
def test_a_language_change_leaves_documents_alone():
    assert "`language`" in step(6)
