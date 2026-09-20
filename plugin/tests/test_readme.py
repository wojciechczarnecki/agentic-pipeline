import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "bin"))

import workflow_config  # noqa: E402
import workflow_metrics  # noqa: E402

README = (PLUGIN / "README.md").read_text()
CHANGELOG = (PLUGIN / "CHANGELOG.md").read_text()


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


# The key list is not copied here: a third copy beside workflow_metrics.COUNTERS and the
# check test's COMPLETE would be one more place to drift.
def test_metrics_block_lists_every_counter():
    section = README.split("## Metryki workflow", 1)[1]
    for counter in [*workflow_metrics.TIMESTAMPS, *workflow_metrics.COUNTERS]:
        assert f"{counter}:" in section, counter


def installation_section() -> str:
    return README.split("## Instalacja", 1)[1].split("\n## ", 1)[0]


def test_installation_pins_the_release_tag():
    section = installation_section()
    assert '"ref"' in section
    assert "pipeline--v" in section
    assert "main" in section


def test_installation_explains_the_marketplace_registration():
    section = installation_section()
    assert "marketplace remove" in section
    assert "marketplace add" in section
    assert "~/.claude/plugins/marketplaces" in section


def test_the_guard_section_states_the_migration_scope():
    section = README.split("### Strażnik komend", 1)[1].split("\n## ", 1)[0]
    for token in ["Alembic", "migrations.command", "migrations.localHosts"]:
        assert token in section, token


def test_the_changelog_names_the_consumer_impact():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    section = CHANGELOG.split(f"## {manifest['version']}", 1)[1].split("\n## ", 1)[0]
    assert "wpływ na konsumenta" in section
