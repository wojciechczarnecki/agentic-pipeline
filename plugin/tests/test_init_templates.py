import json
import os
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
TEMPLATES = PLUGIN / "templates"
sys.path.insert(0, str(PLUGIN / "bin"))

import workflow_config  # noqa: E402

BASE_FILES = [
    "pre-push",
    "settings.json",
    "workflow.example.json",
    "CLAUDE.md",
    "docs/PROJECT.md",
    "docs/ROADMAP.md",
    "docs/BACKLOG.md",
    "docs/DECISIONS.md",
    "docs/CONVENTIONS.md",
]


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
    assert any(key.startswith("pipeline@") for key in settings["enabledPlugins"])


def test_settings_template_names_no_marketplace_of_its_own():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    marketplaces = json.dumps(settings["extraKnownMarketplaces"])
    # A placeholder has to stay visibly a placeholder: a repository that does not exist
    # would leave every initialised project with a marketplace entry that silently fails.
    assert "TODO" in marketplaces
    assert all("TODO" in key for key in settings["enabledPlugins"])


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


def test_backlog_template_carries_priorities_and_triggers():
    text = (TEMPLATES / "docs" / "BACKLOG.md").read_text()
    assert "P1" in text and "P2" in text and "P3" in text
    assert "Wyzwalacz" in text


def test_documents_leave_the_project_specific_parts_open():
    for relative in ["CLAUDE.md", "docs/PROJECT.md", "docs/CONVENTIONS.md"]:
        assert "TODO" in (TEMPLATES / relative).read_text(), relative


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
    # Without `ref` the consumer follows `main` — the pin is the point of the entry.
    assert "ref" in source
    assert "TODO" in name
    assert "TODO" in source["url"]
    assert "TODO" in source["ref"]


def test_settings_template_allows_the_metrics_checker():
    settings = json.loads((TEMPLATES / "settings.json").read_text())
    allow = settings["permissions"]["allow"]
    # Every stage closes by running the checker; a subagent under /pipeline:ship cannot
    # answer a permission prompt, so the pattern has to be allowed up front.
    assert any("workflow_metrics.py" in rule for rule in allow), allow
