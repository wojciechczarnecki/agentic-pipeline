import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CHANGELOG = (PLUGIN / "CHANGELOG.md").read_text()


# SPEC 014, AC29: the three rituals leave, the derived metrics and the scripted close arrive.
# A later bump keeps this green; the section for the manifest version is pinned in
# test_readme.py.
def test_the_manifest_is_at_least_0_9_0():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert tuple(int(part) for part in manifest["version"].split(".")) >= (0, 9, 0)


def test_the_changelog_records_spec_014():
    assert "\n## 0.9.0\n" in CHANGELOG
    section = CHANGELOG.split("\n## 0.9.0\n", 1)[1].split("\n## ", 1)[0]
    for token in [
        "converge pass",
        "Red before the change",
        "chunked implementer",
        "`implement.chunked`",
        "implement-converge-finds-missing-ac",
        "implement-escalates-on-never-red-test",
        "implement-stops-at-group-boundary",
        "--derive",
        "--close",
        "`KIND`",
        "retired",
    ]:
        assert token in section, token
    assert "**consumer impact:**" in section
    impact = " ".join(section.split("**consumer impact:**", 1)[1].split("\n### ", 1)[0].split())
    for token in ["`Pass when:`", "`implement`", "CI"]:
        assert token in impact, token
