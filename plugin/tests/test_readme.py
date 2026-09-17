import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "bin"))

import workflow_config  # noqa: E402

README = (PLUGIN / "README.md").read_text()
CHANGELOG = (PLUGIN / "CHANGELOG.md").read_text()

REQUIRED_SECTIONS = [
    "## Instalacja",
    "## Komendy i agenci",
    "## Konfiguracja projektu",
    "### Strażnik komend",
    "## Mechanika pipeline'u",
    "### Statusy speca",
    "### Kontrakt `RESULT`",
    "### Wyzwalacze eskalacji",
    "## Metryki workflow",
    "## Testy pluginu",
    "## CHANGELOG",
]


def flatten(data: dict, prefix: str = "") -> dict[str, object]:
    flat: dict[str, object] = {}
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, f"{dotted}."))
        else:
            flat[dotted] = value
    return flat


DEFAULTS = flatten(workflow_config.defaults())


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_are_present(section):
    assert section in README, section


@pytest.mark.parametrize("key, value", sorted(DEFAULTS.items()))
def test_every_config_key_is_documented_with_its_default(key, value):
    rows = [line for line in README.splitlines() if line.startswith(f"| `{key}`")]
    assert len(rows) == 1, key
    assert f"`{json.dumps(value)}`" in rows[0], (key, rows[0])


def test_the_optional_migrations_section_is_documented():
    rows = [line for line in README.splitlines() if line.startswith("| `migrations`")]
    assert len(rows) == 1
    assert "brak sekcji" in rows[0]
    assert "localHosts" in rows[0]


def test_every_schema_key_reaches_the_table():
    documented = {line.split("`")[1] for line in README.splitlines() if line.startswith("| `")}
    for key in workflow_config.SCHEMA:
        assert key in documented or any(entry.startswith(f"{key}.") for entry in documented), key


def test_installation_covers_a_local_path_and_a_repository():
    section = README.split("## Instalacja", 1)[1].split("\n## ", 1)[0]
    assert "--plugin-dir" in section
    assert "claude plugin marketplace add" in section
    assert "/plugin install pipeline@" in section


def test_changelog_starts_at_the_manifest_version():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert f"## {manifest['version']}" in CHANGELOG
    assert manifest["version"] in README


def test_metrics_block_lists_every_counter():
    counters = [
        "started_at",
        "plan_steps",
        "plan_review_blockers",
        "plan_review_majors",
        "plan_changes",
        "implement_steps",
        "implement_iterations",
        "deviations",
        "escalations",
        "final_review_blockers",
        "final_review_worth_fixing",
        "final_review_nits",
        "findings_accepted",
        "findings_rejected",
        "finished_at",
    ]
    section = README.split("## Metryki workflow", 1)[1]
    for counter in counters:
        assert f"{counter}:" in section, counter
