import json
import re
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "bin"))

import workflow_config  # noqa: E402
import workflow_metrics  # noqa: E402

README = (PLUGIN / "README.md").read_text()
CHANGELOG = (PLUGIN / "CHANGELOG.md").read_text()
INSTALL = (PLUGIN / "docs" / "INSTALL.md").read_text()


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
    assert "no section" in rows[0]
    assert "localHosts" in rows[0]


def test_every_schema_key_reaches_the_table():
    documented = {line.split("`")[1] for line in README.splitlines() if line.startswith("| `")}
    for key in workflow_config.SCHEMA:
        assert key in documented or any(entry.startswith(f"{key}.") for entry in documented), key


def test_installation_covers_a_local_path_and_a_repository():
    section = install_guide()
    assert "--plugin-dir" in section
    assert "claude plugin marketplace add" in section
    assert "/plugin install pipeline@" in section


def test_changelog_starts_at_the_manifest_version():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert f"## {manifest['version']}" in CHANGELOG


# The key list is not copied here: a third copy beside workflow_metrics.COUNTERS and the
# check test's COMPLETE would be one more place to drift.
def test_metrics_block_lists_every_counter():
    section = README.split("## Workflow metrics", 1)[1]
    for counter in [*workflow_metrics.TIMESTAMPS, *workflow_metrics.COUNTERS]:
        assert f"{counter}:" in section, counter


def install_guide() -> str:
    return INSTALL


# The marketplace `ref` is global per machine and `install`/`update` take no version, so a
# tag pin meant `marketplace remove` and a reinstall in every project on each release
# (docs/DECISIONS.md, 2026-09-21). The channel, the user scope and the update path are
# what replaced it.
def test_installation_follows_the_stable_channel():
    section = install_guide()
    assert '"ref": "stable"' in section
    assert "#stable" in section
    assert "main" in section
    assert '"ref": "pipeline--v' not in section


def test_installation_defaults_to_the_user_scope():
    section = install_guide()
    assert "--scope user" in section
    assert "version isolation" not in section, "project scope is not an offered option"
    assert "claude plugin marketplace update" in section
    assert "claude plugin update pipeline@" in section


def test_installation_explains_the_one_time_migration():
    section = install_guide()
    assert "marketplace remove" in section
    assert "marketplace add" in section
    assert "known_marketplaces.json" in section
    assert "git checkout -- .claude/settings.json" in section


def test_installation_explains_opting_a_repository_out():
    section = install_guide()
    assert '"pipeline@wcz-tools": false' in section


# The declared settings enable nothing: `enabledPlugins: true` made every session in the
# repository install a `--scope project` duplicate beside the user install, stuck on its
# old version (docs/DECISIONS.md, 2026-09-21).
def test_installation_does_not_enable_the_plugin_in_the_project():
    section = install_guide()
    assert '"pipeline@wcz-tools": true' not in section
    assert "claude plugin uninstall pipeline@<name> --scope project" in section
    assert "git checkout -- .claude/settings.json" in section


def test_install_guide_covers_verification_and_init():
    guide = install_guide()
    for token in [
        "claude plugin list",
        "/pipeline:init",
        "--permission-mode bypassPermissions",
        "extraKnownMarketplaces",
    ]:
        assert token in guide, token


# A deliberate copy of `command_lines` in tests/test_documents.py (no cross-directory import
# of test modules, PLAN 003 Approach): a change to how commands are counted goes into both.
def command_count(section: str) -> int:
    count, fenced = 0, False
    for line in section.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        command = re.sub(r"\s+#.*$", "", line).strip()
        if fenced and command and not command.startswith("#"):
            count += 1 + len(re.findall(r"&&|\|\||;", command))
    return count


def test_command_count_counts_joined_commands():
    block = "```bash\n# a comment\na && b\nc; d || e   # trailing; comment\n\n```\nf && g\n"
    assert command_count(block) == 5


# The README keeps the shortest path in; everything else is behind the link (SPEC 003, AC10).
def test_the_installation_section_is_short_and_links_the_guide():
    section = README.split("## Installation", 1)[1].split("\n## ", 1)[0]
    assert command_count(section) <= 3
    assert "](docs/INSTALL.md)" in section
    commands = fenced_commands(section)
    for token in ["#stable", "--scope user", "/pipeline:init"]:
        assert any(token in command for command in commands), (token, commands)
    # every command of the short section is the guide's own, so the two cannot drift apart
    missing = [command for command in commands if command not in INSTALL]
    assert not missing, missing


def fenced_commands(section: str) -> list[str]:
    commands, fenced = [], False
    for line in section.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        command = re.sub(r"\s+#.*$", "", line).strip()
        if fenced and command and not command.startswith("#"):
            commands.append(command)
    return commands


def test_the_guard_section_states_the_migration_scope():
    section = README.split("### Command guard", 1)[1].split("\n## ", 1)[0]
    for token in ["Alembic", "migrations.command", "migrations.localHosts"]:
        assert token in section, token


def test_the_changelog_names_the_consumer_impact():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    section = CHANGELOG.split(f"## {manifest['version']}", 1)[1].split("\n## ", 1)[0]
    assert "**consumer impact:**" in section


POLISH = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def strip_code(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    # An unclosed fence would hide the rest of the text from every check that strips code.
    assert not fenced, "unbalanced code fence"
    return re.sub(r"`[^`\n]*`", "", "\n".join(kept))


# Quoted literals the Polish skills produce (`## Decyzje właściciela`) stay verbatim inside
# code spans; everything around them is English.
@pytest.mark.parametrize(
    "document",
    [
        "README.md",
        "docs/GUARD.md",
        "docs/INSTALL.md",
        "CHANGELOG.md",
    ],
)
def test_no_polish_outside_code(document):
    text = strip_code((PLUGIN / document).read_text())
    found = sorted(POLISH & set(text))
    assert not found, (document, found)


def section(text: str, heading: str) -> str:
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]


# The section map quotes the Polish literals verbatim (docs/DECISIONS.md, 2026-09-21); they
# are the only Polish the README may carry, and only inside code spans.
def test_readme_polish_only_in_the_section_map():
    mapped = section(README, "### Section map")
    outside = README.replace(mapped, "")
    assert not sorted(POLISH & set(outside))
    assert not sorted(POLISH & set(strip_code(mapped)))


def section_map() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in section(README, "### Section map").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        # Three cells are the severity rows; any other count is a broken map row that would
        # otherwise drop out of every parity check unnoticed.
        assert len(cells) in (3, 4), line
        if len(cells) == 3:
            continue
        key, document, polish, english = cells
        rows.append((key.strip("`"), document, polish[1:-1], english[1:-1]))
    return rows


def test_the_language_contract_names_three_groups():
    contract = section(README, "### Language contract")
    groups = [
        "Follows `language`",
        "Always English",
        "Follows the Claude Code session language",
    ]
    positions = [contract.index(group) for group in groups]
    assert positions == sorted(positions)
    for token in [
        "SPEC",
        "PLAN",
        "PR descriptions",
        "commit messages",
        "PR titles",
        "branch names",
        "RESULT",
        "metric keys",
        "severity tokens",
        "questions",
        "escalations",
    ]:
        assert token in contract, token


def test_the_section_map_is_well_formed():
    rows = section_map()
    assert {document for _, document, _, _ in rows} == {"SPEC", "PLAN"}
    for document in ("SPEC", "PLAN"):
        keys = [key for key, doc, _, _ in rows if doc == document]
        assert len(keys) == len(set(keys)), document
    for line in section(README, "### Section map").splitlines():
        if line.startswith("| `") and line.count("|") == 5:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            for cell in cells[2:]:
                assert re.fullmatch(r"`[^`]+`", cell), line
    for _, _, _, english in rows:
        assert not POLISH & set(english), english
    severities = {}
    for line in section(README, "### Section map").splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if line.startswith("| `") and len(cells) == 3:
            severities[cells[0].strip("`")] = cells[2]
    assert set(severities) == {"blocker", "major", "minor", "worth-fixing", "nit"}
    assert "`warto poprawić`" in severities["worth-fixing"]


HEADINGS = [
    "## Installation",
    "## Commands and agents",
    "## Project configuration — `.claude/workflow.json`",
    "### Formatting (`format[]`)",
    "### Command guard",
    "## Pipeline mechanics",
    "### Spec statuses",
    "### The `RESULT` contract",
    "### Escalation triggers",
    "### Language contract",
    "### Section map",
    "## Workflow metrics",
    "### Checking metrics (`--check`)",
    "## CHANGELOG",
]


def test_the_readme_keeps_its_sections():
    lines = README.splitlines()
    positions = [lines.index(heading) for heading in HEADINGS if heading in lines]
    assert len(positions) == len(HEADINGS), [h for h in HEADINGS if h not in lines]
    assert positions == sorted(positions)


@pytest.mark.parametrize(
    "status", ["spec-draft", "spec-ready", "plan-draft", "plan-approved", "implemented", "done"]
)
def test_every_status_is_documented(status):
    section = README.split("### Spec statuses", 1)[1].split("\n### ", 1)[0]
    assert any(line.startswith(f"| `{status}`") for line in section.splitlines()), status


def result_block(text: str) -> str:
    return text.split("```\nRESULT: DONE | ESCALATE", 1)[1].split("```", 1)[0]


def result_fields(block: str) -> list[str]:
    return [line.split(":", 1)[0] for line in block.splitlines() if line.strip()]


# The field names are the contract the orchestrator parses; the placeholders after them only
# describe the values, so the README gives them in English while the ship skill is Polish.
def test_the_result_block_matches_the_contract():
    ship = (PLUGIN / "skills" / "ship" / "SKILL.md").read_text()
    assert result_fields(result_block(README)) == result_fields(result_block(ship))
    assert result_fields(result_block(README)) == ["STATUS", "METRICS", "ESCALATION", "SUMMARY"]


def test_the_guard_section_links_guard_md():
    section = README.split("### Command guard", 1)[1].split("\n## ", 1)[0]
    assert "](docs/GUARD.md)" in section
    assert (PLUGIN / "docs" / "GUARD.md").is_file()


# From 0.4.0 the guard refuses detaching the plugin in an agent session (SPEC 005, AC18);
# the install guide must send the owner to a terminal for the commands it shows.
def test_install_guide_leaves_detaching_to_the_owners_terminal():
    for token in ["terminal", "agent session", "refuse", "protectedBranches"]:
        assert token in INSTALL, token
