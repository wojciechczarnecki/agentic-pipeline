import json
import os
import re
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
TEMPLATES = PLUGIN / "templates"
sys.path.insert(0, str(PLUGIN / "bin"))

import workflow_config  # noqa: E402
from test_readme import POLISH  # noqa: E402

SHARED_FILES = ["pre-push", "settings.json", "workflow.example.json"]
LANGUAGES = ("en", "pl")
DOCUMENTS = [
    "CLAUDE",
    "docs/PROJECT",
    "docs/ROADMAP",
    "docs/BACKLOG",
    "docs/DECISIONS",
    "docs/CONVENTIONS",
]
LANGUAGE_FILES = [f"{document}.{language}.md" for document in DOCUMENTS for language in LANGUAGES]
BASE_FILES = SHARED_FILES + LANGUAGE_FILES


@pytest.mark.parametrize("relative", BASE_FILES)
def test_base_templates_exist_and_parse(relative):
    path = TEMPLATES / relative
    assert path.is_file(), relative
    assert path.read_text().strip()
    if path.suffix == ".json":
        json.loads(path.read_text())


def test_the_pre_push_template_is_executable():
    assert os.access(TEMPLATES / "pre-push", os.X_OK)


def test_settings_template_leaves_hooks_to_the_plugin():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    assert "hooks" not in settings
    assert set(settings["permissions"]) == {"allow", "ask", "deny"}
    assert settings["extraKnownMarketplaces"]


# A session started in a directory whose settings enable the plugin installs it at
# `--scope project` on its own, beside the user install, and `plugin update --scope user`
# never lifts that copy (docs/DECISIONS.md, 2026-09-21). The template declares the source
# only; `false` is the one legitimate value, the opt-out.
def test_settings_template_does_not_enable_the_plugin():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    assert all(value is False for value in settings.get("enabledPlugins", {}).values())
    entries = settings["extraKnownMarketplaces"]
    assert [entry["source"]["ref"] for entry in entries.values()] == ["stable"]


def test_settings_template_names_no_marketplace_of_its_own():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    marketplaces = json.dumps(settings["extraKnownMarketplaces"])
    # A placeholder has to stay visibly a placeholder: a repository that does not exist
    # would leave every initialised project with a marketplace entry that silently fails.
    assert "TODO" in marketplaces


def test_settings_template_protects_the_guardrail_files():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    ask = " ".join(settings["permissions"]["ask"])
    assert ".claude/settings" in ask
    # Project configuration, not an enforcement mechanism: init has to write it unattended.
    assert ".claude/workflow.json" not in ask


def test_workflow_example_covers_every_key_and_validates(tmp_path):
    example = json.loads((TEMPLATES / "workflow.example.json").read_text())
    assert set(example) == set(workflow_config.SCHEMA)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "workflow.json").write_text(json.dumps(example))
    config = workflow_config.load(tmp_path)
    assert config.found
    assert config.get("docs.specsDir") == "specs"


@pytest.mark.parametrize("language, trigger", [("en", "Trigger"), ("pl", "Wyzwalacz")])
def test_backlog_template_carries_priorities_and_triggers(language, trigger):
    text = (TEMPLATES / "docs" / f"BACKLOG.{language}.md").read_text()
    assert "P1" in text and "P2" in text and "P3" in text
    assert trigger in text


@pytest.mark.parametrize("language", LANGUAGES)
def test_documents_leave_the_project_specific_parts_open(language):
    for document in ["CLAUDE", "docs/PROJECT", "docs/CONVENTIONS"]:
        relative = f"{document}.{language}.md"
        assert "TODO" in (TEMPLATES / relative).read_text(), relative


def heading_levels(text: str) -> list[str]:
    levels, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            levels.append(line.split(" ", 1)[0])
    return levels


# `init` copies the template for the `language` it was given (SPEC 006, AC11): the two
# languages are one document, so a section or a placeholder added to one has to reach the
# other.
@pytest.mark.parametrize("document", DOCUMENTS)
def test_language_twins_share_their_structure(document):
    english = (TEMPLATES / f"{document}.en.md").read_text()
    polish = (TEMPLATES / f"{document}.pl.md").read_text()
    assert heading_levels(english) == heading_levels(polish)
    assert english.count("TODO") == polish.count("TODO")


@pytest.mark.parametrize("document", DOCUMENTS)
def test_english_init_templates_have_no_polish(document):
    text = (TEMPLATES / f"{document}.en.md").read_text()
    # Unstripped: the English templates carry no Polish even in code.
    found = sorted(POLISH & set(text))
    assert not found, (document, found)


# SPEC 006, AC14: commit messages, PR titles and branch names are English for every
# consumer, so the conventions state it instead of leaving it open; the documentation follows
# `language`, and the conversation is the session's.
@pytest.mark.parametrize(
    "language, heading, commits, session",
    [
        ("en", "## Language", "Commit messages", "session"),
        ("pl", "## Język", "Komunikaty", "sesji"),
    ],
)
def test_conventions_state_the_language_rules(language, heading, commits, session):
    text = (TEMPLATES / "docs" / f"CONVENTIONS.{language}.md").read_text()
    rules = text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]
    commit_line = next(line for line in rules.splitlines() if line.startswith(f"- {commits}"))
    assert "TODO" not in commit_line
    assert "PR" in commit_line
    assert "`language`" in rules
    assert f'`language: "{language}"`' in rules
    assert session in rules


GITHUB = TEMPLATES / "github"
CI_VARIANTS = {
    "ci-python.yml": ["uv sync", "uv run pytest", "uv run ruff check"],
    "ci-node.yml": ["npm ci", "npm run test", "npm run lint", "npm run build"],
    "ci-placeholder.yml": ["TODO:"],
}


@pytest.mark.parametrize("name, fragments", sorted(CI_VARIANTS.items()))
def test_ci_variants_match_detected_stack(name, fragments):
    text = (GITHUB / "workflows" / name).read_text()
    for fragment in fragments:
        assert fragment in text, (name, fragment)
    assert "continue-on-error:" not in text
    assert "pull_request" in text and "branches: [main]" in text


def job_names(name: str) -> list[str]:
    names, inside = [], False
    for line in (GITHUB / "workflows" / name).read_text().splitlines():
        if line.startswith("jobs:"):
            inside = True
        elif inside and line.startswith("  ") and not line.startswith("   ") and ":" in line:
            names.append(line.strip().rstrip(":"))
        elif inside and line and not line.startswith(" "):
            break
    return names


def test_ci_variants_carry_separate_job_names():
    names = [name for variant in CI_VARIANTS for name in job_names(variant)]
    assert names
    assert len(names) == len(set(names)), names


@pytest.mark.parametrize(
    "name, fragment",
    [("security-python.yml", "pip-audit"), ("security-node.yml", "npm audit")],
)
def test_security_variants(name, fragment):
    text = (GITHUB / "workflows" / name).read_text()
    assert fragment in text
    assert "schedule:" in text and "workflow_dispatch:" in text


def test_dependabot_template():
    text = (GITHUB / "dependabot.yml").read_text()
    assert text.count("interval: monthly") == 3
    assert text.count("update-types: [minor, patch]") == 2
    assert text.count('update-types: ["version-update:semver-major"]') == 2
    assert "package-ecosystem: github-actions" in text
    assert "package-ecosystem: uv" in text
    assert "package-ecosystem: npm" in text


def test_settings_template_pins_a_git_https_source():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    entries = settings["extraKnownMarketplaces"]
    assert len(entries) == 1
    name, entry = next(iter(entries.items()))
    source = entry["source"]
    assert source["source"] == "git"
    assert source["url"].endswith(".git") and "https://" in source["url"]
    # Without `ref` the consumer follows `main`; `stable` is the release channel the owner
    # moves to each new tag, so it is a real value rather than a placeholder.
    assert source["ref"] == "stable"
    assert "TODO" in name
    assert "TODO" in source["url"]


def test_settings_template_allows_the_metrics_checker():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    allow = settings["permissions"]["allow"]
    # Every stage closes by running the checker; a subagent under /pipeline:ship cannot
    # answer a permission prompt, so the pattern has to be allowed up front.
    # The rule matches the PATH form the skills call. ${CLAUDE_PLUGIN_ROOT} is not
    # substituted in permission rules, so a rule spelled with it never matches anything.
    # The pattern is a prefix: a wildcard on both sides of `workflow_metrics.py` would
    # auto-approve any command merely containing that text.
    assert "Bash(workflow_metrics.py *)" in allow, allow
    assert not any("CLAUDE_PLUGIN_ROOT" in rule for rule in allow), allow
    assert not any(rule.startswith("Bash(python3 *") for rule in allow), allow


# Stages read their templates and the section map from the plugin at run time (SPEC 007,
# AC6); a stage subagent cannot answer the prompt, so the rule is allowed up front, spelled
# with the same marketplace placeholder init fills in for `extraKnownMarketplaces`.
def test_settings_template_allows_reading_the_plugin():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    rules = [rule for rule in settings["permissions"]["allow"] if rule.startswith("Read(")]
    assert len(rules) == 1, rules
    match = re.fullmatch(r"Read\(~/\.claude/plugins/cache/([^/]+)/pipeline/\*\*\)", rules[0])
    assert match, rules[0]
    assert [match.group(1)] == list(settings["extraKnownMarketplaces"])


# SPEC 012, AC5: the example shows the switch, off.
def test_the_example_shows_chunking_off():
    example = json.loads((TEMPLATES / "workflow.example.json").read_text())
    assert example["implement"] == {"chunked": False}
