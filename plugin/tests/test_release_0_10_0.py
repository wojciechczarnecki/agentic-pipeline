import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CHANGELOG = (PLUGIN / "CHANGELOG.md").read_text()


# SPEC 015, AC20: bootstrapping and the guard. A later bump keeps this green; the section for
# the manifest version is pinned in test_readme.py.
def test_the_manifest_is_at_least_0_10_0():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert tuple(int(part) for part in manifest["version"].split(".")) >= (0, 10, 0)


def test_the_changelog_records_spec_015():
    assert "\n## 0.10.0\n" in CHANGELOG
    section = CHANGELOG.split("\n## 0.10.0\n", 1)[1].split("\n## ", 1)[0]
    for token in [
        "init-subdirectory-project",
        ".github/repository/",
        ".gitignore",
        "interpreter",
        "alembic.ini",
        "separate calls",
        "placeholder",
    ]:
        assert token in section, token
    assert "**consumer impact:**" in section
    impact = " ".join(section.split("**consumer impact:**", 1)[1].split("\n### ", 1)[0].split())
    for token in ["`ask`", "`deny`", "newly initialised", "by hand"]:
        assert token in impact, token
